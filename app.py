from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta
import numpy as np

app = Flask(__name__)

@app.route('/predict', methods=['POST'])
def predict():
    """
    Predict satellite position at a specific time.
    
    Required parameters:
    - initial_time_utc: Initial time in UTC format (YYYY-MM-DD HH:MM:SS)
    - initial_position: Initial position as 3D vector [x, y, z] in meters
    - velocity: Velocity as 3D vector [vx, vy, vz] in m/s
    - final_time_utc: Final time in UTC format (YYYY-MM-DD HH:MM:SS)
    
    Optional parameters:
    - a_earth: Earth semi-major axis in meters (default: 6378137.0)
    - b_earth: Earth semi-minor axis in meters (default: 6356752.3142)
    
    Returns:
    - final_position: Predicted position as 3D vector {x, y, z} in meters
    - initial_time_utc: Initial time in UTC format
    - final_time_utc: Final time in UTC format
    """
    try:
        data = request.json
        
        # Extract required parameters from request
        initial_time_utc = data.get('initial_time_utc')
        initial_position = data.get('initial_position')
        velocity = data.get('velocity')
        final_time_utc = data.get('final_time_utc')
        
        # Optional parameters with defaults
        a_earth = data.get('a_earth', 6378137.0)
        b_earth = data.get('b_earth', 6356752.3142)
        
        # Validate inputs
        if not all([initial_time_utc, initial_position, velocity, final_time_utc]):
            return jsonify({"error": "Missing required parameters"}), 400
            
        if len(initial_position) != 3 or len(velocity) != 3:
            return jsonify({"error": "Position and velocity must be 3D vectors"}), 400
        
        # Calculate position
        final_position = predict_satellite_position(
            initial_time_utc,
            initial_position, 
            velocity, 
            final_time_utc, 
            a_earth, 
            b_earth
        )
        
        # Return as JSON
        return jsonify({
            "final_position": {
                "x": final_position[0],
                "y": final_position[1],
                "z": final_position[2]
            },
            "initial_time_utc": initial_time_utc,
            "final_time_utc": final_time_utc
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def predict_satellite_position(initial_time_utc, initial_position, velocity, final_time_utc, 
                               a_earth=6378137.0, b_earth=6356752.3142):
    """
    Calculate satellite position at a specific time using orbital mechanics.
    
    Args:
        initial_time_utc (str): Initial time in UTC format (YYYY-MM-DD HH:MM:SS)
        initial_position (list): Initial position as 3D vector [x, y, z] in meters
        velocity (list): Velocity as 3D vector [vx, vy, vz] in m/s
        final_time_utc (str): Final time in UTC format (YYYY-MM-DD HH:MM:SS)
        a_earth (float): Earth semi-major axis in meters (default: 6378137.0)
        b_earth (float): Earth semi-minor axis in meters (default: 6356752.3142)
        
    Returns:
        tuple: Final position as 3D vector (x, y, z) in meters
    """
    initial_time = datetime.strptime(initial_time_utc, "%Y-%m-%d %H:%M:%S")
    final_time = datetime.strptime(final_time_utc, "%Y-%m-%d %H:%M:%S")
    time_difference = (final_time - initial_time).total_seconds()
    
    initial_position = np.array(initial_position)
    velocity = np.array(velocity)
    
    r = np.linalg.norm(initial_position)
    v = np.linalg.norm(velocity)
    
    h = np.cross(initial_position, velocity)
    
    mu = 3.986004418e14
    e_vec = np.cross(velocity, h) / mu - initial_position / r
    e = np.linalg.norm(e_vec)
    
    n = np.sqrt(mu / (r ** 3))
    M = n * time_difference
    
    E = M
    for i in range(10):
        E = E - (E - e * np.sin(E) - M) / (1 - e * np.cos(E))
    
    nu = 2 * np.arctan(np.sqrt((1 + e)/(1 - e)) * np.tan(E/2))
    
    r_new = r * (1 + e * np.cos(nu))
    
    f = (a_earth - b_earth) / a_earth
    J2 = 1.08263e-3
    
    perturbation = np.zeros(3)
    perturbation[0] = -1.5 * J2 * (mu/r_new**2) * (a_earth/r_new)**2 * (1 - 5*(initial_position[2]/r_new)**2) * initial_position[0]/r_new
    perturbation[1] = -1.5 * J2 * (mu/r_new**2) * (a_earth/r_new)**2 * (1 - 5*(initial_position[2]/r_new)**2) * initial_position[1]/r_new
    perturbation[2] = -1.5 * J2 * (mu/r_new**2) * (a_earth/r_new)**2 * (3 - 5*(initial_position[2]/r_new)**2) * initial_position[2]/r_new
    
    final_position = initial_position + velocity * time_difference + 0.5 * perturbation * time_difference**2
    
    return tuple(final_position)

@app.route('/track', methods=['POST'])
def track_over_time():
    """
    Track satellite position over a time period.
    
    Required parameters:
    - initial_time_utc: Initial time in UTC format (YYYY-MM-DD HH:MM:SS)
    - initial_position: Initial position as 3D vector [x, y, z] in meters
    - velocity: Velocity as 3D vector [vx, vy, vz] in m/s
    
    Optional parameters:
    - duration_days: Duration of tracking in days (default: 30)
    - interval_hours: Time interval between points in hours (default: 6)
    - a_earth: Earth semi-major axis in meters (default: 6378137.0)
    - b_earth: Earth semi-minor axis in meters (default: 6356752.3142)
    
    Returns:
    - satellite_track: Array of position data points over time
    - initial_time_utc: Initial time in UTC format
    - total_points: Number of data points in the track
    - interval_hours: Time interval between points
    """
    try:
        data = request.json
        
        # Extract required parameters
        initial_time_utc = data.get('initial_time_utc')
        initial_position = data.get('initial_position')
        velocity = data.get('velocity')
        duration_days = data.get('duration_days', 30)
        interval_hours = data.get('interval_hours', 6)
        
        # Optional parameters
        a_earth = data.get('a_earth', 6378137.0)
        b_earth = data.get('b_earth', 6356752.3142)
        
        # Validate inputs
        if not all([initial_time_utc, initial_position, velocity]):
            return jsonify({"error": "Missing required parameters"}), 400
            
        if len(initial_position) != 3 or len(velocity) != 3:
            return jsonify({"error": "Position and velocity must be 3D vectors"}), 400
        
        # Generate tracking data
        initial_time = datetime.strptime(initial_time_utc, "%Y-%m-%d %H:%M:%S")
        tracking_data = []
        
        # Add the initial position as the first point
        tracking_data.append({
            "time_utc": initial_time_utc,
            "position": {
                "x": float(initial_position[0]),
                "y": float(initial_position[1]),
                "z": float(initial_position[2])
            }
        })
        
        for i in range(interval_hours, int(duration_days * 24), interval_hours):
            current_time = initial_time + timedelta(hours=i)
            current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
            
            position = predict_satellite_position(
                initial_time_utc,
                initial_position,
                velocity,
                current_time_str,
                a_earth,
                b_earth
            )
            
            # Convert numpy values to Python native types to ensure JSON serialization
            tracking_data.append({
                "time_utc": current_time_str,
                "position": {
                    "x": float(position[0]),
                    "y": float(position[1]),
                    "z": float(position[2])
                }
            })
        
        return jsonify({
            "satellite_track": tracking_data,
            "initial_time_utc": initial_time_utc,
            "total_points": len(tracking_data),
            "interval_hours": interval_hours
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def home():
    """Render the API documentation page."""
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Satellite Tracking API</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1000px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f9f9f9;
            }
            h1, h2, h3 {
                color: #2c3e50;
            }
            h1 {
                border-bottom: 2px solid #3498db;
                padding-bottom: 10px;
                margin-bottom: 30px;
            }
            .endpoint {
                background-color: white;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 30px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            }
            pre {
                background-color: #f5f5f5;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
                border-left: 4px solid #3498db;
            }
            code {
                font-family: 'Courier New', Courier, monospace;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            th {
                background-color: #f2f2f2;
            }
            .method {
                display: inline-block;
                padding: 5px 10px;
                border-radius: 4px;
                font-weight: bold;
                margin-right: 10px;
            }
            .post {
                background-color: #4CAF50;
                color: white;
            }
            .get {
                background-color: #2196F3;
                color: white;
            }
            .url {
                font-family: 'Courier New', Courier, monospace;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <h1>Satellite Tracking API</h1>
        
        <p>This API provides satellite position prediction capabilities using orbital mechanics and perturbation models.</p>
        
        <div class="endpoint">
            <h2><span class="method post">POST</span><span class="url">/predict</span></h2>
            <p>Predict satellite position at a specific time.</p>
            
            <h3>Request Parameters</h3>
            <table>
                <tr>
                    <th>Parameter</th>
                    <th>Type</th>
                    <th>Required</th>
                    <th>Description</th>
                </tr>
                <tr>
                    <td>initial_time_utc</td>
                    <td>String</td>
                    <td>Yes</td>
                    <td>Initial time in UTC format (YYYY-MM-DD HH:MM:SS)</td>
                </tr>
                <tr>
                    <td>initial_position</td>
                    <td>Array[3]</td>
                    <td>Yes</td>
                    <td>Initial position as 3D vector [x, y, z] in meters</td>
                </tr>
                <tr>
                    <td>velocity</td>
                    <td>Array[3]</td>
                    <td>Yes</td>
                    <td>Velocity as 3D vector [vx, vy, vz] in m/s</td>
                </tr>
                <tr>
                    <td>final_time_utc</td>
                    <td>String</td>
                    <td>Yes</td>
                    <td>Final time in UTC format (YYYY-MM-DD HH:MM:SS)</td>
                </tr>
                <tr>
                    <td>a_earth</td>
                    <td>Float</td>
                    <td>No</td>
                    <td>Earth semi-major axis in meters (default: 6378137.0)</td>
                </tr>
                <tr>
                    <td>b_earth</td>
                    <td>Float</td>
                    <td>No</td>
                    <td>Earth semi-minor axis in meters (default: 6356752.3142)</td>
                </tr>
            </table>
            
            <h3>Example Request</h3>
            <pre><code>{
    "initial_time_utc": "2025-03-03 07:59:04",
    "initial_position": [-33555551.4376850766, -2752187.0749757504, 5223462.178809359],
    "velocity": [3574.1780002673, -6667.4289866602, -1209.3362749905],
    "final_time_utc": "2025-04-03 02:49:25"
}</code></pre>
            
            <h3>Example Response</h3>
            <pre><code>{
    "final_position": {
        "x": -12345678.123,
        "y": 23456789.456,
        "z": 3456789.789
    },
    "initial_time_utc": "2025-03-03 07:59:04",
    "final_time_utc": "2025-04-03 02:49:25"
}</code></pre>
        </div>
        
        <div class="endpoint">
            <h2><span class="method post">POST</span><span class="url">/track</span></h2>
            <p>Track satellite position over a time period.</p>
            
            <h3>Request Parameters</h3>
            <table>
                <tr>
                    <th>Parameter</th>
                    <th>Type</th>
                    <th>Required</th>
                    <th>Description</th>
                </tr>
                <tr>
                    <td>initial_time_utc</td>
                    <td>String</td>
                    <td>Yes</td>
                    <td>Initial time in UTC format (YYYY-MM-DD HH:MM:SS)</td>
                </tr>
                <tr>
                    <td>initial_position</td>
                    <td>Array[3]</td>
                    <td>Yes</td>
                    <td>Initial position as 3D vector [x, y, z] in meters</td>
                </tr>
                <tr>
                    <td>velocity</td>
                    <td>Array[3]</td>
                    <td>Yes</td>
                    <td>Velocity as 3D vector [vx, vy, vz] in m/s</td>
                </tr>
                <tr>
                    <td>duration_days</td>
                    <td>Integer</td>
                    <td>No</td>
                    <td>Duration of tracking in days (default: 30)</td>
                </tr>
                <tr>
                    <td>interval_hours</td>
                    <td>Integer</td>
                    <td>No</td>
                    <td>Time interval between points in hours (default: 6)</td>
                </tr>
                <tr>
                    <td>a_earth</td>
                    <td>Float</td>
                    <td>No</td>
                    <td>Earth semi-major axis in meters (default: 6378137.0)</td>
                </tr>
                <tr>
                    <td>b_earth</td>
                    <td>Float</td>
                    <td>No</td>
                    <td>Earth semi-minor axis in meters (default: 6356752.3142)</td>
                </tr>
            </table>
            
            <h3>Example Request</h3>
            <pre><code>{
    "initial_time_utc": "2025-03-03 07:59:04",
    "initial_position": [-33555551.4376850766, -2752187.0749757504, 5223462.178809359],
    "velocity": [3574.1780002673, -6667.4289866602, -1209.3362749905],
    "duration_days": 7,
    "interval_hours": 12
}</code></pre>
            
            <h3>Example Response</h3>
            <pre><code>{
    "satellite_track": [
        {
            "time_utc": "2025-03-03 07:59:04",
            "position": {
                "x": -33555551.4376850766,
                "y": -2752187.0749757504,
                "z": 5223462.178809359
            }
        },
        {
            "time_utc": "2025-03-03 19:59:04",
            "position": {
                "x": -12345678.123,
                "y": 23456789.456,
                "z": 3456789.789
            }
        },
        ...
    ],
    "initial_time_utc": "2025-03-03 07:59:04",
    "total_points": 15,
    "interval_hours": 12
}</code></pre>
        </div>
        
        <h2>Implementation Notes</h2>
        <ul>
            <li>The API uses a simplified orbital mechanics model with J2 perturbation.</li>
            <li>All positions are in Earth-centered inertial (ECI) reference frame.</li>
            <li>Time format must be exactly "YYYY-MM-DD HH:MM:SS" in UTC.</li>
            <li>Position coordinates are in meters, velocities in meters per second.</li>
        </ul>
    </body>
    </html>
    """)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
