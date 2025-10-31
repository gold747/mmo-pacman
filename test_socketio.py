"""
Simple Socket.IO test to verify the connection and basic functionality
"""
from flask import Flask
from flask_socketio import SocketIO, emit
import time

# Create a minimal Flask app for testing
app = Flask(__name__)
app.config['SECRET_KEY'] = 'test_key'

# Initialize SocketIO with minimal configuration
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# Test event handlers
@socketio.on('connect')
def test_connect():
    print("✅ CLIENT CONNECTED successfully!")
    emit('test_response', {'message': 'Connection successful'})

@socketio.on('disconnect')
def test_disconnect():
    print("❌ Client disconnected")

@socketio.on('test_event')
def handle_test_event(data):
    print(f"📨 Received test event: {data}")
    emit('test_response', {'message': f'Server received: {data}'})

@app.route('/')
def test_page():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Socket.IO Test</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.5/socket.io.js"></script>
    </head>
    <body>
        <h1>Socket.IO Connection Test</h1>
        <div id="status">Connecting...</div>
        <button onclick="testEvent()">Send Test Event</button>
        <div id="log"></div>
        
        <script>
            const socket = io();
            const statusDiv = document.getElementById('status');
            const logDiv = document.getElementById('log');
            
            function log(message) {
                logDiv.innerHTML += '<p>' + message + '</p>';
            }
            
            socket.on('connect', function() {
                statusDiv.innerHTML = '✅ Connected!';
                statusDiv.style.color = 'green';
                log('Connected to server');
            });
            
            socket.on('disconnect', function() {
                statusDiv.innerHTML = '❌ Disconnected';
                statusDiv.style.color = 'red';
                log('Disconnected from server');
            });
            
            socket.on('test_response', function(data) {
                log('Received: ' + data.message);
            });
            
            function testEvent() {
                socket.emit('test_event', 'Hello from client!');
                log('Sent test event');
            }
        </script>
    </body>
    </html>
    '''

if __name__ == '__main__':
    print("🚀 Starting Socket.IO test server...")
    print("📍 Navigate to http://localhost:5001 to test")
    print("🔍 Watch console for connection events")
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)