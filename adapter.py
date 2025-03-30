# adapter.py - Environment and deployment adapter
import os
import logging
import socket
import threading
from urllib.parse import urlparse

# Configure logger
logger = logging.getLogger(__name__)

class PaymentAdapter:
    """
    Adapter to handle different payment environments (local, dev, production)
    """
    def __init__(self, app=None):
        self.app = app
        self.config = {
            'api_key': os.environ.get('LIPIA_API_KEY', '7c8a3202ae14857e71e3a9db78cf62139772cae6'),
            'api_base_url': os.environ.get('LIPIA_API_URL', 'https://lipia-api.kreativelabske.com/api'),
            'payment_url': os.environ.get('PAYMENT_URL', 'https://lipia-online.vercel.app/link/andikartill'),
            'callback_host': os.environ.get('CALLBACK_HOST', '0.0.0.0'),
            'callback_port': int(os.environ.get('CALLBACK_PORT', 8000)),
            'public_url': os.environ.get('PUBLIC_URL', None),
        }
        
        # Set default server type based on environment
        if os.environ.get('RAILWAY_STATIC_URL'):
            self.server_type = 'railway'
        elif os.environ.get('RENDER_EXTERNAL_URL'):
            self.server_type = 'render'
        elif os.environ.get('VERCEL_URL'):
            self.server_type = 'vercel'
        else:
            self.server_type = 'local'
            
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
        app.payment_adapter = self
        
        # Set up callback URL based on environment
        self.setup_callback_url()
        
        # Log configuration
        with app.app_context():
            app.logger.info(f"Payment Adapter initialized for {self.server_type} environment")
            app.logger.info(f"API Base URL: {self.config['api_base_url']}")
            app.logger.info(f"Callback URL: {self.get_callback_url()}")
    
    def setup_callback_url(self):
        """Set up the callback URL based on the deployment environment"""
        if self.config['public_url']:
            # Use explicit public URL if provided
            self.config['public_url'] = self.config['public_url'].rstrip('/')
            return
            
        # Determine public URL based on environment
        if self.server_type == 'railway':
            self.config['public_url'] = f"https://{os.environ.get('RAILWAY_STATIC_URL')}"
        elif self.server_type == 'render':
            self.config['public_url'] = os.environ.get('RENDER_EXTERNAL_URL')
        elif self.server_type == 'vercel':
            self.config['public_url'] = f"https://{os.environ.get('VERCEL_URL')}"
        else:
            # Local development - will be populated dynamically
            self.config['public_url'] = None
    
    def get_callback_url(self, path='/payment/callback'):
        """Get the full callback URL including path"""
        if not self.config['public_url']:
            # Local development - use localhost with port
            return f"http://localhost:{self.config['callback_port']}{path}"
            
        return f"{self.config['public_url']}{path}"
    
    def get_api_key(self):
        """Get the API key for the current environment"""
        return self.config['api_key']
        
    def get_api_url(self, endpoint=None):
        """Get the full API URL for a specific endpoint"""
        base = self.config['api_base_url'].rstrip('/')
        if endpoint:
            endpoint = endpoint.lstrip('/')
            return f"{base}/{endpoint}"
        return base
    
    def find_available_port(self, start_port=8000, end_port=9000):
        """Find an available port for the callback server"""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        for port in range(start_port, end_port):
            try:
                s.bind((self.config['callback_host'], port))
                s.close()
                self.config['callback_port'] = port
                return port
            except Exception:
                continue
        s.close()
        return None

    def get_payment_url(self):
        """Get the payment URL"""
        return self.config['payment_url']