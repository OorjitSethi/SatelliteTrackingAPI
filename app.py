# Import required libraries
from flask import Flask, request, jsonify, render_template_string  # Flask web framework
from datetime import datetime, timedelta  # For handling dates and times
import numpy as np  # For numerical computations
import math  # For mathematical operations

# Initialize Flask application
app = Flask(__name__)

# Define route for predicting satellite position
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
        # Get JSON data from request
        data = request.json
        
        # Extract required parameters from request
        initial_time_utc = data.get('initial_time_utc')
        initial_position = data.get('initial_position')
        velocity = data.get('velocity')
        final_time_utc = data.get('final_time_utc')
        
        # Extract optional parameters with default values
        a_earth = data.get('a_earth', 6378137.0)
        b_earth = data.get('b_earth', 6356752.3142)
        
        # Validate that all required parameters are present
        if not all([initial_time_utc, initial_position, velocity, final_time_utc]):
            return jsonify({"error": "Missing required parameters"}), 400
            
        # Validate that position and velocity are 3D vectors
        if len(initial_position) != 3 or len(velocity) != 3:
            return jsonify({"error": "Position and velocity must be 3D vectors"}), 400
        
        # Calculate final satellite position using orbital mechanics
        final_position = predict_satellite_position(
            initial_time_utc,
            initial_position, 
            velocity, 
            final_time_utc, 
            a_earth, 
            b_earth
        )
        
        # Format and return results as JSON
        return jsonify({
            "final_position": {
                "x": float(final_position[0]),
                "y": float(final_position[1]),
                "z": float(final_position[2])
            },
            "initial_time_utc": initial_time_utc,
            "final_time_utc": final_time_utc
        })
        
    except Exception as e:
        # Return error message if anything goes wrong
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
    # Convert time strings to datetime objects and calculate time difference
    initial_time = datetime.strptime(initial_time_utc, "%Y-%m-%d %H:%M:%S")
    final_time = datetime.strptime(final_time_utc, "%Y-%m-%d %H:%M:%S")
    time_difference = (final_time - initial_time).total_seconds()
    
    # Convert inputs to numpy arrays for vector calculations
    initial_position = np.array(initial_position, dtype=float)
    velocity = np.array(velocity, dtype=float)
    
    # Calculate magnitude of position and velocity vectors
    r = np.linalg.norm(initial_position)
    v = np.linalg.norm(velocity)
    
    # Calculate angular momentum vector
    h = np.cross(initial_position, velocity)
    
    # Standard gravitational parameter for Earth (m³/s²)
    mu = 3.986004418e14
    
    # Calculate eccentricity vector and magnitude
    e_vec = np.cross(velocity, h) / mu - initial_position / r
    e = np.linalg.norm(e_vec)
    
    # Avoid numerical issues when eccentricity is close to 1
    if abs(e - 1.0) < 1e-10:
        e = 0.999999
    
    # Calculate semi-major axis
    a = r / (1 - e * np.dot(e_vec, initial_position) / (e * r))
    
    # For hyperbolic/parabolic orbits, use simple propagation
    if a <= 0:
        final_position = initial_position + velocity * time_difference
        return tuple(final_position)
    
    # Calculate mean motion and mean anomaly
    n = np.sqrt(mu / (a ** 3))
    M = n * time_difference
    
    # Solve Kepler's equation iteratively
    # Different methods for low vs high eccentricity
    if e < 0.8:
        # For low eccentricity, use standard iteration
        E = M
        for i in range(20):  # Increased max iterations
            delta = (E - e * np.sin(E) - M) / (1 - e * np.cos(E))
            E = E - delta
            if abs(delta) < 1e-10:
                break
    else:
        # For high eccentricity, use different initial guess
        E = math.pi if M > math.pi else M
        for i in range(20):
            delta = (E - e * np.sin(E) - M) / (1 - e * np.cos(E))
            E = E - delta
            if abs(delta) < 1e-10:
                break
    
    # Calculate true anomaly from eccentric anomaly
    cos_E = np.cos(E)
    sin_E = np.sin(E)
    cos_nu = (cos_E - e) / (1 - e * cos_E)
    sin_nu = (np.sqrt(1 - e*e) * sin_E) / (1 - e * cos_E)
    nu = np.arctan2(sin_nu, cos_nu)
    
    # Calculate new radius
    r_new = a * (1 - e * cos_E)
    
    # Calculate semi-parameter
    p = a * (1 - e*e)
    
    # Check for zero angular momentum
    h_mag = np.linalg.norm(h)
    if h_mag < 1e-10:
        # If angular momentum too small, use simple propagation
        final_position = initial_position + velocity * time_difference
        return tuple(final_position)
    
    # Calculate unit vectors for coordinate transformation
    h_unit = h / h_mag
    e_unit = e_vec / max(np.linalg.norm(e_vec), 1e-10)
    n_unit = np.cross([0, 0, 1], h_unit)
    n_mag = np.linalg.norm(n_unit)
    
    # Handle equatorial orbits specially
    if n_mag < 1e-10:
        n_unit = np.array([1, 0, 0])
    else:
        n_unit = n_unit / n_mag
    
    # Complete orthogonal coordinate system
    m_unit = np.cross(h_unit, n_unit)
    
    # Calculate position in orbital plane
    x_orb = r_new * cos_nu
    y_orb = r_new * sin_nu
    
    # Transform position to inertial frame
    pos_vec = x_orb * n_unit + y_orb * m_unit
    
    # Calculate J2 perturbation effects
    f = (a_earth - b_earth) / a_earth
    J2 = 1.08263e-3
    
    # Calculate perturbation vector components
    perturbation = np.zeros(3)
    perturbation[0] = -1.5 * J2 * (mu/r_new**2) * (a_earth/r_new)**2 * (1 - 5*(pos_vec[2]/r_new)**2) * pos_vec[0]/r_new
    perturbation[1] = -1.5 * J2 * (mu/r_new**2) * (a_earth/r_new)**2 * (1 - 5*(pos_vec[2]/r_new)**2) * pos_vec[1]/r_new
    perturbation[2] = -1.5 * J2 * (mu/r_new**2) * (a_earth/r_new)**2 * (3 - 5*(pos_vec[2]/r_new)**2) * pos_vec[2]/r_new
    
    # For very long time periods, use simpler model
    if abs(time_difference) > 30 * 24 * 3600:  # More than 30 days
        final_position = initial_position + velocity * time_difference
    else:
        # Add perturbation effects to position
        final_position = pos_vec + 0.5 * perturbation * time_difference**2
    
    return tuple(final_position)

# Define route for tracking satellite over time
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
        # Get JSON data from request
        data = request.json
        
        # Extract required parameters
        initial_time_utc = data.get('initial_time_utc')
        initial_position = data.get('initial_position')
        velocity = data.get('velocity')
        duration_days = data.get('duration_days', 30)
        interval_hours = data.get('interval_hours', 6)
        
        # Extract optional parameters
        a_earth = data.get('a_earth', 6378137.0)
        b_earth = data.get('b_earth', 6356752.3142)
        
        # Validate required inputs
        if not all([initial_time_utc, initial_position, velocity]):
            return jsonify({"error": "Missing required parameters"}), 400
            
        if len(initial_position) != 3 or len(velocity) != 3:
            return jsonify({"error": "Position and velocity must be 3D vectors"}), 400
        
        # Initialize tracking data array
        initial_time = datetime.strptime(initial_time_utc, "%Y-%m-%d %H:%M:%S")
        tracking_data = []
        
        # Add initial position as first point
        tracking_data.append({
            "time_utc": initial_time_utc,
            "position": {
                "x": float(initial_position[0]),
                "y": float(initial_position[1]),
                "z": float(initial_position[2])
            }
        })
        
        # Calculate positions at regular intervals
        for i in range(interval_hours, int(duration_days * 24), interval_hours):
            current_time = initial_time + timedelta(hours=i)
            current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Calculate position at current time
            position = predict_satellite_position(
                initial_time_utc,
                initial_position,
                velocity,
                current_time_str,
                a_earth,
                b_earth
            )
            
            # Add position to tracking data
            tracking_data.append({
                "time_utc": current_time_str,
                "position": {
                    "x": float(position[0]),
                    "y": float(position[1]),
                    "z": float(position[2])
                }
            })
        
        # Return tracking results
        return jsonify({
            "satellite_track": tracking_data,
            "initial_time_utc": initial_time_utc,
            "total_points": len(tracking_data),
            "interval_hours": interval_hours
        })
        
    except Exception as e:
        # Return error if anything goes wrong
        return jsonify({"error": str(e)}), 500

# Define route for home page
@app.route('/', methods=['GET'])
def home():
    """Render the API documentation page."""
    # Return HTML template with API documentation
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

# Run the Flask application if this file is run directly
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
