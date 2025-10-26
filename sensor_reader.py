import serial
import requests
import json
import time

# --- USER: Apna COM Port yahan enter karo ---
# Windows par 'COM3', 'COM4', etc.
# Linux par '/dev/ttyUSB0'
# Mac par '/dev/cu.usbserial-...'
SERIAL_PORT = 'COM3'  # <--- APNA COM PORT YAHAN BADLO
BAUD_RATE = 115200

# Server URL jahan data bhejna hai
SERVER_URL = "http://127.0.0.1:5000/update_sensors"

def connect_to_serial(port, baud):
    print(f"Connecting to {port} at {baud} baud...")
    try:
        ser = serial.Serial(port, baud, timeout=2)
        print("Connected! Waiting for data...")
        return ser
    except serial.SerialException as e:
        print(f"Error: Could not open port {port}. {e}")
        print("Please check your COM port and make sure no other program (like Arduino Monitor) is using it.")
        return None

def main():
    ser = connect_to_serial(SERIAL_PORT, BAUD_RATE)
    if ser is None:
        input("Press Enter to exit...")
        return

    while True:
        try:
            # Serial se ek line padho
            line = ser.readline().decode('utf-8').strip()

            if line:
                # print(f"Raw data: {line}") # Debugging ke liye
                try:
                    # JSON data ko parse karo
                    data = json.loads(line)
                    if "error" in data:
                        print(f"Sensor Error: {data['error']}")
                        continue
                    
                    print(f"Read data: Temp={data['temp']}°C, Humidity={data['humidity']}%")

                    # Server ko data POST karo
                    try:
                        requests.post(SERVER_URL, json=data, timeout=1)
                    except requests.exceptions.RequestException as e:
                        print(f"Error sending data to server: {e}")

                except json.JSONDecodeError:
                    print(f"Garbage data (not JSON): {line}")
            
            time.sleep(0.1) # Thoda pause

        except serial.SerialException:
            print("Serial port disconnected. Reconnecting...")
            ser.close()
            time.sleep(5)
            ser = connect_to_serial(SERIAL_PORT, BAUD_RATE)
            if ser is None:
                break
        except KeyboardInterrupt:
            print("Stopping...")
            break
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            time.sleep(2)

    if ser and ser.is_open:
        ser.close()
    print("Script stopped.")

if __name__ == "__main__":
    main()  