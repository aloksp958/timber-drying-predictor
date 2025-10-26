from flask import Flask, request, jsonify, render_template, Response, make_response
import subprocess
import json
import sys
import os
import csv
from datetime import datetime, timedelta
import threading
import time
import serial
from fpdf import FPDF

app = Flask(__name__)

# --- Global variable to store sensor data ---
latest_sensor_data = { "temp": 25.0, "humidity": 50.0, "status": "disconnected" }
sensor_thread = None
stop_sensor_thread = threading.Event()

# --- Placeholder function for reading sensor ---
# (read_sensor_data_loop function remains the same)
def read_sensor_data_loop():
    global latest_sensor_data; SERIAL_PORT = 'COM3'; BAUD_RATE = 115200
    while not stop_sensor_thread.is_set():
        ser = None
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
            if latest_sensor_data["status"] != "connected": print("(Sensor Thread) Connected!"); latest_sensor_data["status"] = "connected"
            while not stop_sensor_thread.is_set():
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    try:
                        data = json.loads(line)
                        if "error" in data:
                            if latest_sensor_data["temp"] != "Error": print(f"(Sensor Thread) Sensor Error: {data['error']}")
                            latest_sensor_data["temp"] = "Error"; latest_sensor_data["humidity"] = "Error"; latest_sensor_data["status"] = "error"
                        else:
                            latest_sensor_data["temp"] = round(float(data['temp']), 1); latest_sensor_data["humidity"] = round(float(data['humidity']), 1); latest_sensor_data["status"] = "connected"
                    except (json.JSONDecodeError, ValueError, TypeError) as e: pass
                time.sleep(0.1)
        except serial.SerialException:
            if latest_sensor_data["status"] != "disconnected": print(f"(Sensor Thread) Port {SERIAL_PORT} disconnected. Retrying..."); latest_sensor_data["status"] = "disconnected"; latest_sensor_data["temp"] = "N/A"; latest_sensor_data["humidity"] = "N/A"
        except Exception as e:
             if latest_sensor_data["status"] != "error": print(f"(Sensor Thread) An unexpected error occurred: {e}"); latest_sensor_data["status"] = "error"
        finally:
             if ser and ser.is_open: ser.close()
        if not stop_sensor_thread.is_set(): time.sleep(5)
    print("(Sensor Thread) Stopped.")


# --- Webpage Routes ---
@app.route('/')
def home(): return render_template('index.html')

@app.route('/dashboard')
def dashboard(): return render_template('dashboard.html')

# --- API Routes ---
# (/get_sensors, /predict, /log_prediction routes remain the same)
@app.route('/get_sensors', methods=['GET'])
def get_sensors():
    response = jsonify(latest_sensor_data); response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"; return response

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.json; species = data['species']; thickness = data['thickness']; initial_mc = data['initial_mc']; target_mc = data['target_mc']
        try: temp_c = float(latest_sensor_data["temp"])
        except (ValueError, TypeError): temp_c = 25.0
        try: humidity_rh = float(latest_sensor_data["humidity"])
        except (ValueError, TypeError): humidity_rh = 50.0
        command = [ sys.executable, 'predict.py', species, str(thickness), str(initial_mc), str(target_mc), str(temp_c), str(humidity_rh) ]
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')
        return jsonify({'success': True, 'prediction_output': result.stdout})
    except subprocess.CalledProcessError as e: return jsonify({'success': False, 'error': e.stderr or e.stdout})
    except Exception as e: return jsonify({'success': False, 'error': str(e)})

@app.route('/log_prediction', methods=['POST'])
def log_prediction():
    try:
        data = request.json; log_file = 'prediction_log.csv'; file_exists = os.path.isfile(log_file)
        with open(log_file, 'a', newline='', encoding='utf-8') as f:
            headers = ['Timestamp', 'Species', 'Thickness_cm', 'Initial_Moisture', 'Target_Moisture', 'Temperature_C', 'Humidity_RH', 'Predicted_Hours']
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
            if not file_exists or os.path.getsize(log_file) == 0: writer.writeheader()
            timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            row_data = { 'Timestamp': timestamp_str, 'Species': data.get('species'), 'Thickness_cm': data.get('thickness'), 'Initial_Moisture': data.get('initial_mc'), 'Target_Moisture': data.get('target_mc'), 'Temperature_C': data.get('temp_c'), 'Humidity_RH': data.get('humidity_rh'), 'Predicted_Hours': data.get('predicted_hours') }
            writer.writerow(row_data)
        return jsonify({'success': True, 'message': 'Logged successfully!'})
    except Exception as e: return jsonify({'success': False, 'error': f"Logging failed: {e}"})

# --- NAYA: /get_active_jobs mein SORTING aur BETTER COST ---
@app.route('/get_active_jobs', methods=['GET'])
def get_active_jobs():
    log_file = 'prediction_log.csv'; jobs = []; now = datetime.now()
    BASE_COST_RATE_PER_HOUR = 0.5 # Example: ₹0.5 per hour base rate
    TEMP_COST_FACTOR = 0.02 # Example: 2% cost increase per degree above 25°C

    try:
        if not os.path.isfile(log_file): return jsonify([])
        with open(log_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, skipinitialspace=True)
            for i, row in enumerate(reader):
                try:
                    start_time = datetime.strptime(row['Timestamp'], '%Y-%m-%d %H:%M:%S')
                    predicted_hours = float(row.get('Predicted_Hours', 0))
                    if predicted_hours <= 0: continue # Skip invalid prediction

                    end_time = start_time + timedelta(hours=predicted_hours)
                    time_remaining_delta = end_time - now
                    is_ready = time_remaining_delta.total_seconds() <= 0

                    # Better Cost Calculation
                    try:
                        temp_c_actual = float(row.get('Temperature_C', 25.0)) # Use logged temp
                    except (ValueError, TypeError):
                        temp_c_actual = 25.0 # Fallback if logged temp is invalid
                    
                    # Apply temperature factor (increase cost slightly for higher temps)
                    temp_adjustment = max(0, temp_c_actual - 25.0) # Degrees above 25
                    adjusted_rate = BASE_COST_RATE_PER_HOUR * (1 + (temp_adjustment * TEMP_COST_FACTOR))
                    estimated_cost = round(predicted_hours * adjusted_rate, 2)

                    # Only add active jobs
                    if not is_ready:
                        jobs.append({
                            'id': f"B{start_time.strftime('%y%m%d')}{i+1:03d}",
                            'species': row.get('Species', 'N/A'),
                            'thickness': row.get('Thickness_cm', 'N/A'),
                            'initial_mc': row.get('Initial_Moisture', 'N/A'),
                            'target_mc': row.get('Target_Moisture', 'N/A'),
                            'start_time_iso': start_time.isoformat(),
                            'end_time_iso': end_time.isoformat(),
                            'predicted_hours': predicted_hours, # Already float
                            'is_ready': is_ready, # Always False here
                            'estimated_cost': estimated_cost
                        })
                except (ValueError, KeyError, TypeError) as e: print(f"Skipping malformed row in active jobs: {row} | Error: {e}"); continue

        # --- NAYA: Sorting ---
        # Pehle un jobs ko rakho jinka end time nazdeek hai
        jobs.sort(key=lambda x: x['end_time_iso'])

        response = jsonify(jobs); response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"; return response
    except Exception as e: print(f"Error reading log for active jobs: {e}"); return jsonify([])


# (/get_history and /download_report remain the same as previous correct version)
@app.route('/get_history', methods=['GET'])
def get_history():
    log_file = 'prediction_log.csv'; completed_jobs = []; now = datetime.now()
    try:
        if not os.path.isfile(log_file): return jsonify([])
        with open(log_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, skipinitialspace=True)
            for i, row in enumerate(reader):
                try:
                    start_time_str = row['Timestamp']; start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S'); predicted_hours = float(row['Predicted_Hours']); end_time = start_time + timedelta(hours=predicted_hours)
                    if end_time <= now:
                        completed_jobs.append({ 'batch_id': f"B{start_time.strftime('%y%m%d')}{i+1:03d}", 'timestamp': start_time_str, 'species': row.get('Species', 'N/A'), 'start_time': start_time.strftime('%Y-%m-%d %H:%M'), 'initial_moisture': row.get('Initial_Moisture', 'N/A'), 'final_moisture': row.get('Target_Moisture', 'N/A'), 'predicted_hours': row.get('Predicted_Hours', 'N/A') })
                except (ValueError, KeyError, TypeError) as e: print(f"Skipping malformed row for history: {row} | Error: {e}"); continue
        completed_jobs.sort(key=lambda x: x['start_time'], reverse=True)
        return jsonify(completed_jobs)
    except Exception as e: print(f"Error reading log for history: {e}"); return jsonify([])

@app.route('/download_report/<path:timestamp_str>', methods=['GET'])
def download_report(timestamp_str):
    log_file = 'prediction_log.csv'; batch_data = None
    from urllib.parse import unquote; timestamp_str = unquote(timestamp_str)
    try: target_start_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
    except ValueError: return f"Invalid Timestamp format received: {timestamp_str}", 400
    try:
        if not os.path.isfile(log_file): return "Log file not found", 404
        with open(log_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, skipinitialspace=True)
            for row in reader:
                 try:
                     if row.get('Timestamp') == timestamp_str: batch_data = row; batch_data['start_time_obj'] = target_start_time; break
                 except (KeyError): continue
        if batch_data is None: return f"Data for timestamp '{timestamp_str}' not found in log.", 404

        pdf = FPDF(); pdf.add_page(); pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, f'Drying Report - {timestamp_str}', 0, 1, 'C'); pdf.ln(10)
        pdf.set_font('Arial', '', 12)
        details = [ ("Species:", batch_data.get('Species', 'N/A')), ("Thickness:", f"{batch_data.get('Thickness_cm', 'N/A')} cm"), ("Start Time:", batch_data['start_time_obj'].strftime('%Y-%m-%d %I:%M %p')), ("Initial Moisture:", f"{batch_data.get('Initial_Moisture', 'N/A')}%"), ("Target Moisture:", f"{batch_data.get('Target_Moisture', 'N/A')}%"), ("Avg. Temperature:", f"{batch_data.get('Temperature_C', 'N/A')} °C"), ("Avg. Humidity:", f"{batch_data.get('Humidity_RH', 'N/A')}%"), ("Predicted Drying Time:", f"{float(batch_data.get('Predicted_Hours', 0)):.1f} hours"), ]
        col_width = pdf.w / 2.2; line_height = 8
        for label, value in details: pdf.set_font('Arial', 'B', 11); pdf.cell(col_width / 2.5, line_height, label, 0, 0); pdf.set_font('Arial', '', 11); pdf.cell(col_width, line_height, value, 0, 1)
        pdf.ln(10); pdf.set_font('Arial', 'I', 8); pdf.cell(0, 5, f'Report generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1, 'C')
        pdf_output = pdf.output(dest='S').encode('latin-1')
        response = make_response(pdf_output)
        response.headers['Content-Type'] = 'application/pdf'; response.headers['Content-Disposition'] = f'attachment; filename=report_{timestamp_str.replace(":", "-").replace(" ", "_")}.pdf'
        return response
    except Exception as e: print(f"Error generating PDF for {timestamp_str}: {e}"); import traceback; traceback.print_exc(); return f"Error generating report for {timestamp_str}", 500


# --- Server Start ---
if __name__ == "__main__":
    # print("Starting sensor reading thread...")
    # sensor_thread = threading.Thread(target=read_sensor_data_loop, daemon=True)
    # sensor_thread.start()
    print("Starting Flask server...")
    app.run(debug=True, host='0.0.0.0', use_reloader=False)

    # stop_sensor_thread.set()
    # if sensor_thread: sensor_thread.join()
    # print("Flask server stopped.")

