import os
import csv
import time
from datetime import datetime, timedelta
# Try importing plyer, handle if not installed
try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    print("Warning: 'plyer' library not found. Desktop notifications will be disabled.")
    print("Install it using: pip install plyer")
    PLYER_AVAILABLE = False

LOG_FILE = 'prediction_log.csv'
CHECK_INTERVAL_SECONDS = 60  # Har 60 second mein check karega
notified_jobs = set()  # Jin jobs ka notification bhej diya hai

print("--- Drying Reminder Service Started ---")
print(f"Checking '{LOG_FILE}' every {CHECK_INTERVAL_SECONDS} seconds...")
print("(Is terminal ko chalu rehne dein)")
if not PLYER_AVAILABLE:
    print("!! Desktop notifications are currently DISABLED !!")

def check_jobs_for_notification():
    try:
        if not os.path.isfile(LOG_FILE):
            return

        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            # skipinitialspace=True handles extra spaces
            reader = csv.DictReader(f, skipinitialspace=True)
            # Make sure to read all jobs fresh each time
            jobs = list(reader)

        now = datetime.now()

        for row in jobs:
            try:
                # Use a consistent and robust way to create a unique ID
                timestamp = row.get('Timestamp', '').strip() # Strip spaces here too
                species = row.get('Species', 'unknown')
                thickness = row.get('Thickness_cm', 'unknown')
                job_id = f"{timestamp}-{species}-{thickness}"

                if not timestamp: continue # Skip if timestamp is missing/empty

                if job_id in notified_jobs:
                    continue

                start_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                predicted_hours = float(row['Predicted_Hours'])
                end_time = start_time + timedelta(hours=predicted_hours)

                time_remaining_seconds = (end_time - now).total_seconds()

                if time_remaining_seconds <= 0:
                    print(f"[ALERT] Job '{species}' ({thickness} cm, started {timestamp}) is DONE.")

                    # Desktop notification bhejo ONLY if plyer is available
                    if PLYER_AVAILABLE:
                        print("--> Sending desktop notification...")
                        try:
                            notification.notify(
                                title=f"Drying Batch Ready!",
                                message=f"Your {species} ({thickness} cm) batch (started {timestamp}) is now ready.",
                                app_name="Timber Predictor",
                                timeout=20  # Notification 20 second tak dikhega
                            )
                            notified_jobs.add(job_id) # Add only if notification succeeded
                            print("--> Notification sent successfully.")
                        except Exception as notify_error:
                             print(f"!! Failed to send desktop notification: {notify_error}")
                    else:
                        print("--> Desktop notification disabled (plyer not installed).")
                        # Add to notified_jobs even if plyer isn't installed,
                        # so we don't keep printing the ALERT every minute.
                        notified_jobs.add(job_id)

            except (ValueError, KeyError, TypeError) as e:
                print(f"Error processing row: {e} | Data: {row}")
            except Exception as e:
                print(f"Unexpected error processing row: {e} | Data: {row}")


    except FileNotFoundError:
         print(f"Log file '{LOG_FILE}' not found.")
    except Exception as e:
        print(f"Error reading log file: {e}")

# Main loop
if __name__ == "__main__":
    while True:
        check_jobs_for_notification()
        time.sleep(CHECK_INTERVAL_SECONDS)

# ```
# *(Maine ismein `plyer` library ko check karne ka code bhi add kar diya hai taaki agar woh install na ho toh script crash na ho.)*

# ---

# ### Step 2: Final System Ko Run Karo (2 Terminals Ke Saath)

# Ab aapko hamesha **2 Terminal** chalane honge:

# **Terminal 1: Web Server**
# ```bash
# python app.py
# ```
# *(Yeh aapka web server + dashboard UI + in-app notification sambhalega)*

# **Terminal 2: Reminder Service**
# ```bash
# python reminder_service.py

