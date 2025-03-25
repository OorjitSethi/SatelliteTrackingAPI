# **Satellite Tracking API**

This API predicts and tracks satellite positions using Keplerian orbital mechanics with J2 perturbation effects. It allows users to input an initial satellite state and retrieve its future or tracked positions over time.

## **Features**
- Predicts satellite position at a given time.
- Tracks satellite motion over a duration.
- Accounts for Earth's oblateness (J2 perturbation).
- Returns 3D position vectors in meters.

## **Endpoints**

### **1. Predict Satellite Position**
**URL:**  
`POST /predict`

**Description:**  
Predicts the satellite's position at a given future time.

**Request Body (JSON):**
```json
{
    "initial_time_utc": "2025-03-03 07:59:04",
    "initial_position": [-33555551.4377, -2752187.075, 5223462.1788],
    "velocity": [3574.178, -6667.428, -1209.336],
    "final_time_utc": "2025-04-03 02:49:25"
}
```

**Response (JSON):**
```json
{
    "final_position": {
        "x": -12345678.123,
        "y": 23456789.456,
        "z": 3456789.789
    },
    "initial_time_utc": "2025-03-03 07:59:04",
    "final_time_utc": "2025-04-03 02:49:25"
}
```

---

### **2. Track Satellite Over Time**
**URL:**  
`POST /track`

**Description:**  
Generates a list of positions over a time duration.

**Request Body (JSON):**
```json
{
    "initial_time_utc": "2025-03-03 07:59:04",
    "initial_position": [-33555551.4377, -2752187.075, 5223462.1788],
    "velocity": [3574.178, -6667.428, -1209.336],
    "duration_days": 7,
    "interval_hours": 12
}
```

**Response (JSON - Example):**
```json
{
    "satellite_track": [
        {
            "time_utc": "2025-03-03 07:59:04",
            "position": {
                "x": -33555551.4377,
                "y": -2752187.075,
                "z": 5223462.1788
            }
        },
        {
            "time_utc": "2025-03-03 19:59:04",
            "position": {
                "x": -12345678.123,
                "y": 23456789.456,
                "z": 3456789.789
            }
        }
    ],
    "initial_time_utc": "2025-03-03 07:59:04",
    "total_points": 15,
    "interval_hours": 12
}
```

---

## **Setup and Deployment**

### **1. Run Locally**
#### **Prerequisites**
- Python 3 installed
- Flask installed (`pip install flask numpy`)

#### **Run the API**
```bash
python app.py
```
Access the API at `http://127.0.0.1:5000/`.

---

### **2. Deploy on Render**
1. Push the code to a **GitHub repository**.
2. Go to [Render](https://render.com/) and create a new **Web Service**.
3. Connect to your **GitHub repo**.
4. Set **Build Command**:  
   ```
   pip install -r requirements.txt
   ```
5. Set **Start Command**:  
   ```
   gunicorn app:app
   ```
6. Click **Deploy**.

Your API is now live at `https://your-api.onrender.com/`.

---

### **3. Deploy on AWS EC2**
1. Launch an **EC2 instance** (Ubuntu).
2. SSH into the instance:
   ```bash
   ssh -i your-key.pem ubuntu@your-ec2-ip
   ```
3. Install dependencies:
   ```bash
   sudo apt update
   sudo apt install python3-pip -y
   pip3 install flask numpy gunicorn
   ```
4. Transfer the API code:
   ```bash
   scp -i your-key.pem app.py ubuntu@your-ec2-ip:~
   ```
5. Start the API:
   ```bash
   gunicorn --bind 0.0.0.0:5000 app:app
   ```
6. Access it at `http://your-ec2-ip:5000/`.

---

## **Usage Examples**

### **1. Using Python**
```python
import requests

url = "https://your-api.onrender.com/predict"
data = {
    "initial_time_utc": "2025-03-03 07:59:04",
    "initial_position": [-33555551.4377, -2752187.075, 5223462.1788],
    "velocity": [3574.178, -6667.428, -1209.336],
    "final_time_utc": "2025-04-03 02:49:25"
}

response = requests.post(url, json=data)
print(response.json())
```

---

### **2. Using JavaScript**
```javascript
fetch("https://your-api.onrender.com/predict", {
    method: "POST",
    headers: {
        "Content-Type": "application/json"
    },
    body: JSON.stringify({
        "initial_time_utc": "2025-03-03 07:59:04",
        "initial_position": [-33555551.4377, -2752187.075, 5223462.1788],
        "velocity": [3574.178, -6667.428, -1209.336],
        "final_time_utc": "2025-04-03 02:49:25"
    })
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error("Error:", error));
```

---

## **API Documentation**
For full details, visit the API’s home page at:  
`https://your-api.onrender.com/`

---

## **License**
This project is open-source and can be modified or used under the MIT License.
