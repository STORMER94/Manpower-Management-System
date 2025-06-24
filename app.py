# app.py
import os
import sqlite3
from flask import Flask, request, jsonify, render_template, send_file
import pandas as pd # Required for Excel operations, install with pip install pandas openpyxl
from io import BytesIO # Required for in-memory Excel files

# --- Database Initialization (database.py content integrated here for simplicity) ---
DATABASE = 'manpower_management.db'

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()

        # Stakeholders Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stakeholders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL
            )
        ''')

        # Requests Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_no TEXT UNIQUE NOT NULL,
                requested_by TEXT NOT NULL,
                department TEXT NOT NULL,
                category TEXT NOT NULL,
                request_date TEXT NOT NULL, -- YYYY-MM-DD
                request_title TEXT NOT NULL,
                description TEXT
            )
        ''')

        # RequestUpdates Table (One-to-one with Requests)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS request_updates (
                request_id INTEGER PRIMARY KEY,
                srs_sent_date TEXT, -- YYYY-MM-DD
                srs_approval_date TEXT, -- YYYY-MM-DD
                estimation_received_date TEXT, -- YYYY-MM-DD
                indent_sent_date TEXT, -- YYYY-MM-DD
                signed_indent_received_date TEXT, -- YYYY-MM-DD
                estimated_man_hours_ba INTEGER,
                estimated_man_hours_dev INTEGER,
                estimated_man_hours_tester INTEGER,
                development_start_date TEXT, -- YYYY-MM-DD
                uat_mail_date TEXT, -- YYYY-MM-DD
                uat_confirmation_date TEXT, -- YYYY-MM-DD
                current_status TEXT, -- New field added
                FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE CASCADE
            )
        ''')

        # ActualManHours Table (Many-to-one with Requests, Many-to-one with Stakeholders)
        # Added 'task_date' column
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS actual_man_hours (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL,
                stakeholder_id INTEGER NOT NULL,
                actual_man_hours INTEGER NOT NULL,
                task_date TEXT, -- YYYY-MM-DD, Added for the update man-hours requirement
                FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE CASCADE,
                FOREIGN KEY (stakeholder_id) REFERENCES stakeholders(id) ON DELETE CASCADE
            )
        ''')

        # Add current_status column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE request_updates ADD COLUMN current_status TEXT")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                raise e
        conn.commit()

# --- Flask Application Setup ---
app = Flask(__name__)

# Ensure the database is initialized when the app starts
with app.app_context():
    init_db()

def get_db():
    """Establishes a database connection or returns the existing one."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row # This allows access to columns by name
    return conn

# --- Routes for Stakeholder Master ---

@app.route('/')
def index():
    """Renders the main index page (you can link to different modules from here)."""
    return render_template('index.html')

@app.route('/stakeholders')
def stakeholders_page():
    """Renders the stakeholders management page."""
    return render_template('stakeholders.html')

@app.route('/api/stakeholders', methods=['GET'])
def get_stakeholders():
    """Retrieves all stakeholders."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM stakeholders ORDER BY name ASC')
    stakeholders = cursor.fetchall()
    conn.close()
    return jsonify([dict(s) for s in stakeholders])

@app.route('/api/stakeholders', methods=['POST'])
def add_stakeholder():
    """Adds a new stakeholder."""
    data = request.get_json()
    name = data.get('name')
    role = data.get('role')

    if not name or not role:
        return jsonify({'error': 'Name and Role are required'}), 400

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO stakeholders (name, role) VALUES (?, ?)', (name, role))
        conn.commit()
        return jsonify({'message': 'Stakeholder added successfully', 'id': cursor.lastrowid}), 201
    except sqlite3.IntegrityError:
        conn.rollback()
        return jsonify({'error': 'Stakeholder with this name already exists'}), 409
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/stakeholders/<int:stakeholder_id>', methods=['PUT'])
def update_stakeholder(stakeholder_id):
    """Updates an existing stakeholder."""
    data = request.get_json()
    name = data.get('name')
    role = data.get('role')

    if not name or not role:
        return jsonify({'error': 'Name and Role are required'}), 400

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE stakeholders SET name = ?, role = ? WHERE id = ?', (name, role, stakeholder_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'error': 'Stakeholder not found'}), 404
        return jsonify({'message': 'Stakeholder updated successfully'})
    except sqlite3.IntegrityError:
        conn.rollback()
        return jsonify({'error': 'Stakeholder with this name already exists'}), 409
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/stakeholders/<int:stakeholder_id>', methods=['DELETE'])
def delete_stakeholder(stakeholder_id):
    """Deletes a stakeholder."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM stakeholders WHERE id = ?', (stakeholder_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'error': 'Stakeholder not found'}), 404
        return jsonify({'message': 'Stakeholder deleted successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# --- Routes for Request Master ---

@app.route('/requests')
def requests_page():
    """Renders the requests management page."""
    return render_template('requests.html')


@app.route('/api/requests', methods=['GET'])
def get_requests():
    """Retrieves all requests."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM requests ORDER BY request_date DESC')
    requests = cursor.fetchall()
    conn.close()
    return jsonify([dict(r) for r in requests])

@app.route('/api/requests', methods=['POST'])
def add_request():
    """Adds a new request."""
    data = request.get_json()
    required_fields = ['request_no', 'requested_by', 'department', 'category', 'request_date', 'request_title']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field.replace("_", " ").title()} is required'}), 400

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO requests (request_no, requested_by, department, category, request_date, request_title, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['request_no'], data['requested_by'], data['department'],
            data['category'], data['request_date'], data['request_title'],
            data.get('description', '')
        ))
        conn.commit()
        return jsonify({'message': 'Request added successfully', 'id': cursor.lastrowid}), 201
    except sqlite3.IntegrityError:
        conn.rollback()
        return jsonify({'error': 'Request with this number already exists'}), 409
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/requests/<int:request_id>', methods=['PUT'])
def update_request_master(request_id):
    """Updates an existing request in the Request Master."""
    data = request.get_json()
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Build the update query dynamically based on provided fields
        set_clauses = []
        params = []
        for key, value in data.items():
            if key in ['request_no', 'requested_by', 'department', 'category', 'request_date', 'request_title', 'description']:
                set_clauses.append(f"{key} = ?")
                params.append(value)
        params.append(request_id)

        if not set_clauses:
            return jsonify({'error': 'No valid fields provided for update'}), 400

        query = f"UPDATE requests SET {', '.join(set_clauses)} WHERE id = ?"
        cursor.execute(query, tuple(params))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({'error': 'Request not found'}), 404
        return jsonify({'message': 'Request updated successfully'})
    except sqlite3.IntegrityError:
        conn.rollback()
        return jsonify({'error': 'Request with this name already exists'}), 409
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/requests/<int:request_id>', methods=['DELETE'])
def delete_request(request_id):
    """Deletes a request."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM requests WHERE id = ?', (request_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'error': 'Request not found'}), 404
        return jsonify({'message': 'Request deleted successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/requests/upload', methods=['POST'])
def upload_requests_excel():
    """Uploads requests from an Excel file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        try:
            df = pd.read_excel(file)
            # Ensure column names match exactly or handle mapping
            required_cols = ['Request No', 'Requested By', 'Department', 'Category', 'Request Date', 'Request Title']
            if not all(col in df.columns for col in required_cols):
                return jsonify({'error': 'Missing required columns in Excel file. Ensure "Request No", "Requested By", "Department", "Category", "Request Date", "Request Title" are present.'}), 400

            conn = get_db()
            cursor = conn.cursor()
            inserted_count = 0
            failed_rows = []

            for index, row in df.iterrows():
                try:
                    # Convert date to string YYYY-MM-DD if it's not already
                    request_date = row['Request Date']
                    if pd.isna(request_date): # Handle NaN dates if any
                        request_date_str = None
                    elif isinstance(request_date, pd.Timestamp):
                        request_date_str = request_date.strftime('%Y-%m-%d')
                    else:
                        request_date_str = str(request_date) # Fallback for other formats

                    cursor.execute('''
                        INSERT INTO requests (request_no, requested_by, department, category, request_date, request_title)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        row['Request No'], row['Requested By'], row['Department'],
                        row['Category'], request_date_str, row['Request Title']
                    ))
                    inserted_count += 1
                except sqlite3.IntegrityError:
                    failed_rows.append(f"Row {index+2} (Request No: {row['Request No']}): Duplicate request number.")
                except Exception as e:
                    failed_rows.append(f"Row {index+2} (Request No: {row['Request No']}): Error - {str(e)}")
            conn.commit()
            conn.close()
            
            message = f"Successfully uploaded {inserted_count} requests."
            if failed_rows:
                message += f" Failed to upload {len(failed_rows)} rows due to errors: " + "; ".join(failed_rows)
                return jsonify({'message': message, 'failed_rows': failed_rows}), 200 # Return 200 even if some failed but some succeeded
            return jsonify({'message': message}), 200

        except Exception as e:
            return jsonify({'error': f'Error processing Excel file: {str(e)}'}), 500
    else:
        return jsonify({'error': 'Invalid file type. Please upload an Excel file (.xlsx or .xls)'}), 400

@app.route('/api/requests/download', methods=['GET'])
def download_requests_data():
    """Downloads all existing requests data as an Excel file."""
    conn = get_db()
    df = pd.read_sql_query("SELECT request_no, requested_by, department, category, request_date, request_title, description FROM requests ORDER BY request_date DESC", conn)
    conn.close()

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Requests')
    writer.close() # Use .close() for pandas >= 1.3.0, .save() for older versions
    output.seek(0)

    return send_file(output, download_name='requests_data.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/api/requests/template', methods=['GET'])
def download_requests_template():
    """Downloads an Excel template for Request Master upload."""
    template_data = {
        'Request No': [],
        'Requested By': [],
        'Department': [],
        'Category': [],
        'Request Date': [],
        'Request Title': [],
        'Description': []
    }
    df = pd.DataFrame(template_data)

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Request Template')
    writer.close()
    output.seek(0)

    return send_file(output, download_name='requests_template.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# --- Routes for Update Request ---
@app.route('/update-request')
def update_request_page():
    """Renders the update request page."""
    return render_template('update_request.html')

@app.route('/api/request-details/<int:request_id>', methods=['GET'])
def get_request_details(request_id):
    """Retrieves full details for a single request, including update fields."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            r.id, r.request_no, r.requested_by, r.department, r.category, r.request_date, r.request_title, r.description,
            ru.srs_sent_date, ru.srs_approval_date, ru.estimation_received_date, ru.indent_sent_date,
            ru.signed_indent_received_date, ru.estimated_man_hours_ba, ru.estimated_man_hours_dev,
            ru.estimated_man_hours_tester, ru.development_start_date, ru.uat_mail_date, ru.uat_confirmation_date,
            ru.current_status -- New column
        FROM requests r
        LEFT JOIN request_updates ru ON r.id = ru.request_id
        WHERE r.id = ?
    ''', (request_id,))
    request_details = cursor.fetchone()
    conn.close()

    if request_details:
        return jsonify(dict(request_details))
    return jsonify({'error': 'Request not found'}), 404

@app.route('/api/update-request/<int:request_id>', methods=['PUT'])
def update_request_details(request_id):
    """Updates specific fields for a request in the RequestUpdates table."""
    data = request.get_json()
    conn = get_db()
    cursor = conn.cursor()

    update_fields = [
        'srs_sent_date', 'srs_approval_date', 'estimation_received_date',
        'indent_sent_date', 'signed_indent_received_date',
        'estimated_man_hours_ba', 'estimated_man_hours_dev', 'estimated_man_hours_tester',
        'development_start_date', 'uat_mail_date', 'uat_confirmation_date',
        'current_status' # New field
    ]

    # Filter data to only include valid update fields
    filtered_data = {k: v for k, v in data.items() if k in update_fields}

    if not filtered_data:
        return jsonify({'error': 'No valid fields provided for update'}), 400

    try:
        # Check if an entry already exists in request_updates for this request_id
        cursor.execute('SELECT COUNT(*) FROM request_updates WHERE request_id = ?', (request_id,))
        exists = cursor.fetchone()[0]

        if exists:
            # Update existing record
            set_clauses = [f"{key} = ?" for key in filtered_data.keys()]
            params = list(filtered_data.values())
            params.append(request_id)
            query = f"UPDATE request_updates SET {', '.join(set_clauses)} WHERE request_id = ?"
            cursor.execute(query, tuple(params))
        else:
            # Insert new record
            # Need to ensure all columns are present for INSERT, even if null
            # Dynamically build columns and values for insertion
            columns = ['request_id']
            values = [request_id]
            for field in update_fields:
                columns.append(field)
                values.append(filtered_data.get(field))

            placeholders = ', '.join(['?' for _ in columns])
            col_names = ', '.join(columns)
            query = f"INSERT INTO request_updates ({col_names}) VALUES ({placeholders})"
            cursor.execute(query, tuple(values))

        conn.commit()
        return jsonify({'message': 'Request details updated successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/update-request/download', methods=['GET'])
def download_update_request_data():
    """Downloads all existing request update data as an Excel file."""
    conn = get_db()
    query = '''
        SELECT
            r.request_no,
            r.request_title,
            ru.srs_sent_date,
            ru.srs_approval_date,
            ru.estimation_received_date,
            ru.indent_sent_date,
            ru.signed_indent_received_date,
            ru.estimated_man_hours_ba,
            ru.estimated_man_hours_dev,
            ru.estimated_man_hours_tester,
            ru.development_start_date,
            ru.uat_mail_date,
            ru.uat_confirmation_date,
            ru.current_status -- New column
        FROM requests r
        LEFT JOIN request_updates ru ON r.id = ru.request_id
        ORDER BY r.request_date DESC
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Request Updates')
    writer.close()
    output.seek(0)

    return send_file(output, download_name='request_updates_data.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/api/update-request/template', methods=['GET'])
def download_update_request_template():
    """Downloads an Excel template for updating request details."""
    template_data = {
        'Request No': [],
        'SRS Sent Date': [],
        'SRS Approval Date': [],
        'Estimation Received Date': [],
        'Indent Sent Date': [],
        'Signed Indent Received Date': [],
        'Estimated Man-hours BA': [],
        'Estimated Man-hours Developers': [],
        'Estimated Man-hours Tester': [],
        'Development Start Date': [],
        'UAT Mail Date': [],
        'UAT Confirmation Date': [],
        'Current Status': [] # New field
    }
    df = pd.DataFrame(template_data)

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Update Request Template')
    writer.close()
    output.seek(0)

    return send_file(output, download_name='update_request_template.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/api/update-request/bulk-upload', methods=['POST'])
def bulk_upload_request_updates_excel():
    """Uploads bulk request updates from an Excel file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        try:
            df = pd.read_excel(file)
            expected_cols = [
                'Request No', 'SRS Sent Date', 'SRS Approval Date', 'Estimation Received Date',
                'Indent Sent Date', 'Signed Indent Received Date', 'Estimated Man-hours BA',
                'Estimated Man-hours Developers', 'Estimated Man-hours Tester',
                'Development Start Date', 'UAT Mail Date', 'UAT Confirmation Date',
                'Current Status' # New column
            ]
            # It's okay if not all expected_cols are in the uploaded file, but we should process what's there
            # if not all(col in df.columns for col in expected_cols):
            #     return jsonify({'error': 'Missing required columns in Excel file for bulk update. Ensure all expected columns are present.'}), 400

            conn = get_db()
            cursor = conn.cursor()
            updated_count = 0
            failed_rows = []

            for index, row in df.iterrows():
                request_no = row.get('Request No')
                if pd.isna(request_no):
                    failed_rows.append(f"Row {index+2}: 'Request No' is missing.")
                    continue

                try:
                    cursor.execute('SELECT id FROM requests WHERE request_no = ?', (str(request_no),))
                    req = cursor.fetchone()
                    if not req:
                        failed_rows.append(f"Row {index+2} (Request No: {request_no}): Request No not found in system.")
                        continue
                    request_id = req['id']

                    update_data = {}
                    # Date fields
                    date_fields = {
                        'SRS Sent Date': 'srs_sent_date', 'SRS Approval Date': 'srs_approval_date',
                        'Estimation Received Date': 'estimation_received_date', 'Indent Sent Date': 'indent_sent_date',
                        'Signed Indent Received Date': 'signed_indent_received_date',
                        'Development Start Date': 'development_start_date', 'UAT Mail Date': 'uat_mail_date',
                        'UAT Confirmation Date': 'uat_confirmation_date'
                    }
                    for excel_col, db_col in date_fields.items():
                        if excel_col in row and pd.notna(row.get(excel_col)):
                            date_val = row.get(excel_col)
                            if isinstance(date_val, pd.Timestamp):
                                update_data[db_col] = date_val.strftime('%Y-%m-%d')
                            else:
                                update_data[db_col] = str(date_val)
                        else:
                            update_data[db_col] = None # Ensure explicit NULL for empty date fields

                    # Man-hour fields
                    man_hour_fields = {
                        'Estimated Man-hours BA': 'estimated_man_hours_ba',
                        'Estimated Man-hours Developers': 'estimated_man_hours_dev',
                        'Estimated Man-hours Tester': 'estimated_man_hours_tester'
                    }
                    for excel_col, db_col in man_hour_fields.items():
                        if excel_col in row and pd.notna(row.get(excel_col)):
                            mh_val = row.get(excel_col)
                            try:
                                update_data[db_col] = int(pd.to_numeric(mh_val, errors='raise'))
                            except (ValueError, TypeError):
                                failed_rows.append(f"Row {index+2} (Request No: {request_no}): Invalid numeric value for '{excel_col}'.")
                                continue # Skip this row if man-hours is invalid
                        else:
                            update_data[db_col] = None # Ensure explicit NULL for empty man-hour fields

                    # Current Status field
                    if 'Current Status' in row and pd.notna(row.get('Current Status')):
                        update_data['current_status'] = str(row.get('Current Status'))
                    else:
                        update_data['current_status'] = None


                    # Check if an entry already exists in request_updates for this request_id
                    cursor.execute('SELECT COUNT(*) FROM request_updates WHERE request_id = ?', (request_id,))
                    exists = cursor.fetchone()[0]

                    if exists:
                        set_clauses = [f"{key} = ?" for key in update_data.keys()]
                        params = list(update_data.values())
                        params.append(request_id)
                        query = f"UPDATE request_updates SET {', '.join(set_clauses)} WHERE request_id = ?"
                        cursor.execute(query, tuple(params))
                    else:
                        # For insert, ensure all fields are explicitly present (even if None)
                        # Build columns and values dynamically based on what was *attempted* to be updated
                        all_update_cols_for_insert = ['request_id']
                        insert_values = [request_id]
                        
                        # Add date fields
                        for db_col in date_fields.values():
                            all_update_cols_for_insert.append(db_col)
                            insert_values.append(update_data.get(db_col))
                        
                        # Add man-hour fields
                        for db_col in man_hour_fields.values():
                            all_update_cols_for_insert.append(db_col)
                            insert_values.append(update_data.get(db_col))

                        # Add current_status
                        all_update_cols_for_insert.append('current_status')
                        insert_values.append(update_data.get('current_status'))

                        placeholders = ', '.join(['?' for _ in all_update_cols_for_insert])
                        col_names = ', '.join(all_update_cols_for_insert)
                        query = f"INSERT INTO request_updates ({col_names}) VALUES ({placeholders})"
                        cursor.execute(query, tuple(insert_values))

                    updated_count += 1

                except Exception as e:
                    failed_rows.append(f"Row {index+2} (Request No: {request_no}): Error - {str(e)}")
            conn.commit()
            conn.close()
            
            message = f"Successfully updated {updated_count} request details."
            if failed_rows:
                message += f" Failed to process {len(failed_rows)} rows due to errors: " + "; ".join(failed_rows)
                return jsonify({'message': message, 'failed_rows': failed_rows}), 200
            return jsonify({'message': message}), 200

        except Exception as e:
            return jsonify({'error': f'Error processing Excel file for bulk update: {str(e)}'}), 500
    else:
        return jsonify({'error': 'Invalid file type. Please upload an Excel file (.xlsx or .xls)'}), 400


# --- Routes for Update Man-hours ---
@app.route('/update-manhours')
def update_manhours_page():
    """Renders the update man-hours page."""
    return render_template('update_manhours.html')


@app.route('/api/actual-manhours/upload', methods=['POST'])
def upload_actual_manhours_excel():
    """Uploads actual man-hours from an Excel file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        try:
            df = pd.read_excel(file)
            # Added 'Task Date' to required columns
            required_cols = ['Request No', 'Stakeholder Name', 'Actual Man-Hours', 'Task Date']
            if not all(col in df.columns for col in required_cols):
                return jsonify({'error': 'Missing required columns in Excel file. Ensure "Request No", "Stakeholder Name", "Actual Man-Hours", "Task Date" are present.'}), 400

            conn = get_db()
            cursor = conn.cursor()
            uploaded_count = 0
            failed_rows = []

            for index, row in df.iterrows():
                request_no = row.get('Request No')
                stakeholder_name = row.get('Stakeholder Name')
                actual_man_hours = row.get('Actual Man-Hours')
                task_date_raw = row.get('Task Date') # Get Task Date

                if pd.isna(request_no) or pd.isna(stakeholder_name) or pd.isna(actual_man_hours) or pd.isna(task_date_raw):
                    failed_rows.append(f"Row {index+2}: Missing data in Request No, Stakeholder Name, Actual Man-Hours, or Task Date.")
                    continue

                # Process Actual Man-Hours
                try:
                    processed_actual_man_hours = pd.to_numeric(actual_man_hours, errors='coerce')
                    if pd.isna(processed_actual_man_hours):
                        failed_rows.append(f"Row {index+2} (Request No: {request_no}, Stakeholder: {stakeholder_name}): Invalid 'Actual Man-Hours' value.")
                        continue
                    actual_man_hours_int = int(processed_actual_man_hours)
                except Exception as e:
                    failed_rows.append(f"Row {index+2} (Request No: {request_no}, Stakeholder: {stakeholder_name}): Error processing 'Actual Man-Hours': {str(e)}.")
                    continue

                # Process Task Date
                task_date_str = None
                if pd.notna(task_date_raw):
                    if isinstance(task_date_raw, pd.Timestamp):
                        task_date_str = task_date_raw.strftime('%Y-%m-%d')
                    else:
                        task_date_str = str(task_date_raw) # Fallback

                try:
                    # Get request_id
                    cursor.execute('SELECT id FROM requests WHERE request_no = ?', (request_no,))
                    req = cursor.fetchone()
                    if not req:
                        failed_rows.append(f"Row {index+2} (Request No: {request_no}): Request No not found in system.")
                        continue
                    request_id = req['id']

                    # Get stakeholder_id
                    cursor.execute('SELECT id FROM stakeholders WHERE name = ?', (stakeholder_name,))
                    stk = cursor.fetchone()
                    if not stk:
                        failed_rows.append(f"Row {index+2} (Stakeholder: {stakeholder_name}): Stakeholder not found in system.")
                        continue
                    stakeholder_id = stk['id']

                    # Check if entry already exists for this request_id, stakeholder_id AND task_date
                    cursor.execute('SELECT id FROM actual_man_hours WHERE request_id = ? AND stakeholder_id = ? AND task_date = ?',
                                   (request_id, stakeholder_id, task_date_str))
                    existing_entry = cursor.fetchone()

                    if existing_entry:
                        cursor.execute('''
                            UPDATE actual_man_hours
                            SET actual_man_hours = ?
                            WHERE id = ?
                        ''', (actual_man_hours_int, existing_entry['id']))
                    else:
                        cursor.execute('''
                            INSERT INTO actual_man_hours (request_id, stakeholder_id, actual_man_hours, task_date)
                            VALUES (?, ?, ?, ?)
                        ''', (request_id, stakeholder_id, actual_man_hours_int, task_date_str))
                    uploaded_count += 1

                except Exception as e:
                    failed_rows.append(f"Row {index+2} (Request No: {request_no}, Stakeholder: {stakeholder_name}): Error - {str(e)}")
            conn.commit()
            conn.close()

            message = f"Successfully uploaded/updated {uploaded_count} actual man-hours entries."
            if failed_rows:
                message += f" Failed to process {len(failed_rows)} rows due to errors: " + "; ".join(failed_rows)
                return jsonify({'message': message, 'failed_rows': failed_rows}), 200
            return jsonify({'message': message}), 200

        except Exception as e:
            return jsonify({'error': f'Error processing Excel file: {str(e)}'}), 500
    else:
        return jsonify({'error': 'Invalid file type. Please upload an Excel file (.xlsx or .xls)'}), 400


@app.route('/api/actual-manhours', methods=['GET'])
def get_actual_manhours():
    """Retrieves a list of requests with associated actual man-hours."""
    conn = get_db()
    cursor = conn.cursor()
    # Changed 'r.request_date' to 'amh.task_date'
    cursor.execute('''
        SELECT
            r.request_no,
            amh.task_date, -- Display task_date instead of request_date
            s.name AS stakeholder_name,
            amh.actual_man_hours
        FROM actual_man_hours amh
        JOIN requests r ON amh.request_id = r.id
        JOIN stakeholders s ON amh.stakeholder_id = s.id
        ORDER BY amh.task_date DESC, r.request_no ASC, s.name ASC
    ''')
    data = cursor.fetchall()
    conn.close()
    return jsonify([dict(d) for d in data])

@app.route('/api/actual-manhours/download', methods=['GET'])
def download_actual_manhours_data():
    """Downloads all existing actual man-hours data as an Excel file."""
    conn = get_db()
    query = '''
        SELECT
            r.request_no AS "Request No",
            s.name AS "Stakeholder Name",
            amh.actual_man_hours AS "Actual Man-Hours",
            amh.task_date AS "Task Date"
        FROM actual_man_hours amh
        JOIN requests r ON amh.request_id = r.id
        JOIN stakeholders s ON amh.stakeholder_id = s.id
        ORDER BY amh.task_date DESC, r.request_no ASC, s.name ASC
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Actual Man-Hours Data')
    writer.close()
    output.seek(0)

    return send_file(output, download_name='actual_manhours_data.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/api/actual-manhours/template', methods=['GET'])
def download_actual_manhours_template():
    """Downloads an Excel template for Actual Man-hours upload."""
    template_data = {
        'Request No': [],
        'Stakeholder Name': [],
        'Actual Man-Hours': [],
        'Task Date': []
    }
    df = pd.DataFrame(template_data)

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Man-hours Template')
    writer.close()
    output.seek(0)

    return send_file(output, download_name='manhours_template.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# --- Routes for Report ---
@app.route('/report')
def report_page():
    """Renders the consolidated report page."""
    return render_template('report.html')

@app.route('/api/report', methods=['GET'])
def generate_report():
    """
    Generates the consolidated report with calculated fields,
    applying filters from query parameters if present.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Get filter parameters from request arguments
    request_no_filter = request.args.get('request_no')
    department_filter = request.args.get('department')
    category_filter = request.args.get('category')
    request_date_filter = request.args.get('request_date')
    current_status_filters = request.args.getlist('current_status') # Get list of statuses

    # Base query for the report
    query = '''
        SELECT
            r.id AS request_internal_id, -- Keep internal ID for potential detail view
            r.request_no,
            ru.current_status, -- New column
            r.requested_by,
            r.department,
            r.category,
            r.request_date,
            r.request_title,
            ru.srs_sent_date,
            ru.srs_approval_date,
            ru.estimation_received_date,
            ru.indent_sent_date,
            ru.signed_indent_received_date,
            -- Estimated Man-hours
            COALESCE(ru.estimated_man_hours_ba, 0) AS estimated_man_hours_ba,
            COALESCE(ru.estimated_man_hours_dev, 0) AS estimated_man_hours_developers,
            COALESCE(ru.estimated_man_hours_tester, 0) AS estimated_man_hours_tester,
            
            -- Actual Man-hours (summed by role)
            COALESCE((SELECT SUM(amh.actual_man_hours) FROM actual_man_hours amh JOIN stakeholders s ON amh.stakeholder_id = s.id WHERE amh.request_id = r.id AND s.role = 'BA'), 0) AS actual_man_hours_ba,
            COALESCE((SELECT SUM(amh.actual_man_hours) FROM actual_man_hours amh JOIN stakeholders s ON amh.stakeholder_id = s.id WHERE amh.request_id = r.id AND s.role = 'Developer'), 0) AS actual_man_hours_developers,
            COALESCE((SELECT SUM(amh.actual_man_hours) FROM actual_man_hours amh JOIN stakeholders s ON amh.stakeholder_id = s.id WHERE amh.request_id = r.id AND s.role = 'Tester'), 0) AS actual_man_hours_tester,
            
            -- Calculated Fields
            (COALESCE(ru.estimated_man_hours_ba, 0) + COALESCE(ru.estimated_man_hours_dev, 0) + COALESCE(ru.estimated_man_hours_tester, 0)) AS total_estimated,
            (COALESCE((SELECT SUM(amh.actual_man_hours) FROM actual_man_hours amh JOIN stakeholders s ON amh.stakeholder_id = s.id WHERE amh.request_id = r.id AND s.role = 'BA'), 0) +
             COALESCE((SELECT SUM(amh.actual_man_hours) FROM actual_man_hours amh JOIN stakeholders s ON amh.stakeholder_id = s.id WHERE amh.request_id = r.id AND s.role = 'Developer'), 0) +
             COALESCE((SELECT SUM(amh.actual_man_hours) FROM actual_man_hours amh JOIN stakeholders s ON amh.stakeholder_id = s.id WHERE amh.request_id = r.id AND s.role = 'Tester'), 0)) AS total_actual,
            
            -- Difference: Total Estimated - Total Actual
            ((COALESCE(ru.estimated_man_hours_ba, 0) + COALESCE(ru.estimated_man_hours_dev, 0) + COALESCE(ru.estimated_man_hours_tester, 0)) -
             (COALESCE((SELECT SUM(amh.actual_man_hours) FROM actual_man_hours amh JOIN stakeholders s ON amh.stakeholder_id = s.id WHERE amh.request_id = r.id AND s.role = 'BA'), 0) +
              COALESCE((SELECT SUM(amh.actual_man_hours) FROM actual_man_hours amh JOIN stakeholders s ON amh.stakeholder_id = s.id WHERE amh.request_id = r.id AND s.role = 'Developer'), 0) +
              COALESCE((SELECT SUM(amh.actual_man_hours) FROM actual_man_hours amh JOIN stakeholders s ON amh.stakeholder_id = s.id WHERE amh.request_id = r.id AND s.role = 'Tester'), 0))) AS difference_man_hours,

            ru.development_start_date,
            ru.uat_mail_date,
            ru.uat_confirmation_date,
            
            -- TAT: UAT Mail Date - Development Start date
            CASE
                WHEN ru.uat_mail_date IS NOT NULL AND ru.development_start_date IS NOT NULL THEN
                    JULIANDAY(ru.uat_mail_date) - JULIANDAY(ru.development_start_date)
                ELSE NULL
            END AS tat_days
        FROM requests r
        LEFT JOIN request_updates ru ON r.id = ru.request_id
    '''
    
    conditions = []
    params = []

    if request_no_filter:
        conditions.append("r.request_no LIKE ?")
        params.append(f"%{request_no_filter}%")
    if department_filter:
        conditions.append("r.department LIKE ?")
        params.append(f"%{department_filter}%")
    if category_filter:
        conditions.append("r.category LIKE ?")
        params.append(f"%{category_filter}%")
    if request_date_filter:
        conditions.append("r.request_date = ?")
        params.append(request_date_filter)
    
    if current_status_filters:
        # Handle multiple status selections using IN clause
        placeholders = ','.join('?' * len(current_status_filters))
        conditions.append(f"ru.current_status IN ({placeholders})")
        params.extend(current_status_filters)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " GROUP BY r.id ORDER BY r.request_date DESC" # Group by r.id to handle multiple actual_man_hours entries per request

    cursor.execute(query, tuple(params))
    report_data = cursor.fetchall()
    conn.close()

    report_list = []
    for row in report_data:
        row_dict = dict(row)
        report_list.append(row_dict)

    return jsonify(report_list)


@app.route('/api/report/download', methods=['GET'])
def download_report_data():
    """Downloads the consolidated report data as an Excel file, applying filters if any."""
    conn = get_db()
    cursor = conn.cursor()

    request_no_filter = request.args.get('request_no')
    department_filter = request.args.get('department')
    category_filter = request.args.get('category')
    request_date_filter = request.args.get('request_date')
    current_status_filters = request.args.getlist('current_status')

    query = '''
        SELECT
            r.request_no AS "Request No",
            ru.current_status AS "Current Status", -- New column
            r.requested_by AS "Requested By",
            r.department AS "Department",
            r.category AS "Category",
            r.request_date AS "Request Date",
            r.request_title AS "Request Title",
            ru.srs_sent_date AS "SRS Sent Date",
            ru.srs_approval_date AS "SRS Approval Date",
            ru.estimation_received_date AS "Estimation Received Date",
            ru.indent_sent_date AS "Indent Sent Date",
            ru.signed_indent_received_date AS "Signed Indent Received Date",
            COALESCE(ru.estimated_man_hours_ba, 0) AS "Est. MH BA",
            COALESCE((SELECT SUM(amh.actual_man_hours) FROM actual_man_hours amh JOIN stakeholders s ON amh.stakeholder_id = s.id WHERE amh.request_id = r.id AND s.role = 'BA'), 0) AS "Actual MH BA",
            COALESCE(ru.estimated_man_hours_dev, 0) AS "Est. MH Dev",
            COALESCE((SELECT SUM(amh.actual_man_hours) FROM actual_man_hours amh JOIN stakeholders s ON amh.stakeholder_id = s.id WHERE amh.request_id = r.id AND s.role = 'Developer'), 0) AS "Actual MH Dev",
            COALESCE(ru.estimated_man_hours_tester, 0) AS "Est. MH Tester",
            COALESCE((SELECT SUM(amh.actual_man_hours) FROM actual_man_hours amh JOIN stakeholders s ON amh.stakeholder_id = s.id WHERE amh.request_id = r.id AND s.role = 'Tester'), 0) AS "Actual MH Tester",
            (COALESCE(ru.estimated_man_hours_ba, 0) + COALESCE(ru.estimated_man_hours_dev, 0) + COALESCE(ru.estimated_man_hours_tester, 0)) AS "Total Estimated",
            (COALESCE((SELECT SUM(amh.actual_man_hours) FROM actual_man_hours amh JOIN stakeholders s ON amh.stakeholder_id = s.id WHERE amh.request_id = r.id AND s.role = 'BA'), 0) +
             COALESCE((SELECT SUM(amh.actual_man_hours) FROM actual_man_hours amh JOIN stakeholders s ON amh.stakeholder_id = s.id WHERE amh.request_id = r.id AND s.role = 'Developer'), 0) +
             COALESCE((SELECT SUM(amh.actual_man_hours) FROM actual_man_hours amh JOIN stakeholders s ON amh.stakeholder_id = s.id WHERE amh.request_id = r.id AND s.role = 'Tester'), 0)) AS "Total Actual",
            ((COALESCE(ru.estimated_man_hours_ba, 0) + COALESCE(ru.estimated_man_hours_dev, 0) + COALESCE(ru.estimated_man_hours_tester, 0)) -
             (COALESCE((SELECT SUM(amh.actual_man_hours) FROM actual_man_hours amh JOIN stakeholders s ON amh.stakeholder_id = s.id WHERE amh.request_id = r.id AND s.role = 'BA'), 0) +
              COALESCE((SELECT SUM(amh.actual_man_hours) FROM actual_man_hours amh JOIN stakeholders s ON amh.stakeholder_id = s.id WHERE amh.request_id = r.id AND s.role = 'Developer'), 0) +
              COALESCE((SELECT SUM(amh.actual_man_hours) FROM actual_man_hours amh JOIN stakeholders s ON amh.stakeholder_id = s.id WHERE amh.request_id = r.id AND s.role = 'Tester'), 0))) AS "Difference",
            ru.development_start_date AS "Dev Start Date",
            ru.uat_mail_date AS "UAT Mail Date",
            ru.uat_confirmation_date AS "UAT Conf. Date",
            CASE
                WHEN ru.uat_mail_date IS NOT NULL AND ru.development_start_date IS NOT NULL THEN
                    JULIANDAY(ru.uat_mail_date) - JULIANDAY(ru.development_start_date)
                ELSE NULL
            END AS "TAT (Days)"
        FROM requests r
        LEFT JOIN request_updates ru ON r.id = ru.request_id
    '''
    conditions = []
    params = []

    if request_no_filter:
        conditions.append("r.request_no LIKE ?")
        params.append(f"%{request_no_filter}%")
    if department_filter:
        conditions.append("r.department LIKE ?")
        params.append(f"%{department_filter}%")
    if category_filter:
        conditions.append("r.category LIKE ?")
        params.append(f"%{category_filter}%")
    if request_date_filter:
        conditions.append("r.request_date = ?")
        params.append(request_date_filter)
    
    if current_status_filters:
        # Handle multiple status selections using IN clause
        placeholders = ','.join('?' * len(current_status_filters))
        conditions.append(f"ru.current_status IN ({placeholders})")
        params.extend(current_status_filters)


    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " GROUP BY r.id ORDER BY r.request_date DESC" # Group by r.id

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Consolidated Report')
    writer.close()
    output.seek(0)

    return send_file(output, download_name='consolidated_report.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/api/report/manhours-breakup/<int:request_id>', methods=['GET'])
def get_manhours_breakup(request_id):
    """
    Provides a detailed breakup of actual man-hours for a specific request,
    stakeholder and task date wise, with an optional role filter.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Get optional role filter from query parameters
    role_filter = request.args.get('role')

    base_query = '''
        SELECT
            s.name AS stakeholder_name,
            s.role AS stakeholder_role,
            amh.actual_man_hours,
            amh.task_date
        FROM actual_man_hours amh
        JOIN stakeholders s ON amh.stakeholder_id = s.id
        WHERE amh.request_id = ?
    '''
    params = [request_id]

    if role_filter:
        base_query += ' AND s.role = ?'
        params.append(role_filter)
    
    base_query += ' ORDER BY amh.task_date ASC, s.name ASC'

    cursor.execute(base_query, tuple(params))
    breakup_data = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in breakup_data])

# --- Routes for Dashboard ---
@app.route('/dashboard')
def dashboard_page():
    """Renders the dashboard page."""
    return render_template('dashboard.html')

@app.route('/api/dashboard/data', methods=['GET'])
def get_dashboard_data():
    """Provides aggregated data for dashboard charts."""
    conn = get_db()
    cursor = conn.cursor()

    # Example: Requests by Category
    cursor.execute('SELECT category, COUNT(*) as count FROM requests GROUP BY category')
    requests_by_category = [dict(row) for row in cursor.fetchall()]

    # Example: Estimated vs Actual Man-hours by Role (across all requests)
    cursor.execute('''
        SELECT
            'BA' AS role,
            SUM(COALESCE(ru.estimated_man_hours_ba, 0)) AS estimated,
            SUM(COALESCE(amh_ba.actual_man_hours, 0)) AS actual
        FROM requests r
        LEFT JOIN request_updates ru ON r.id = ru.request_id
        LEFT JOIN actual_man_hours amh_ba ON r.id = amh_ba.request_id
        LEFT JOIN stakeholders s_ba ON amh_ba.stakeholder_id = s_ba.id AND s_ba.role = 'BA'
        GROUP BY 1
        UNION ALL
        SELECT
            'Developer' AS role,
            SUM(COALESCE(ru.estimated_man_hours_dev, 0)) AS estimated,
            SUM(COALESCE(amh_dev.actual_man_hours, 0)) AS actual
        FROM requests r
        LEFT JOIN request_updates ru ON r.id = ru.request_id
        LEFT JOIN actual_man_hours amh_dev ON r.id = amh_dev.request_id
        LEFT JOIN stakeholders s_dev ON amh_dev.stakeholder_id = s_dev.id AND s_dev.role = 'Developer'
        GROUP BY 1
        UNION ALL
        SELECT
            'Tester' AS role,
            SUM(COALESCE(ru.estimated_man_hours_tester, 0)) AS estimated,
            SUM(COALESCE(amh_tester.actual_man_hours, 0)) AS actual
        FROM requests r
        LEFT JOIN request_updates ru ON r.id = ru.request_id
        LEFT JOIN actual_man_hours amh_tester ON r.id = amh_tester.request_id
        LEFT JOIN stakeholders s_tester ON amh_tester.stakeholder_id = s_tester.id AND s_tester.role = 'Tester'
        GROUP BY 1
    ''')
    man_hours_comparison = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return jsonify({
        'requests_by_category': requests_by_category,
        'man_hours_comparison': man_hours_comparison
    })


if __name__ == '__main__':
    app.run(debug=True)