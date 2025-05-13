"""
Script to update the application routes to use the new Replit Auth implementation.
Run this script to switch from the old to the new implementation.
"""
from app import app
from flask import Blueprint
import replit_auth_new

# Create the new blueprint
replit_blueprint = replit_auth_new.create_replit_blueprint()

# Register the blueprint
app.register_blueprint(replit_blueprint, url_prefix="/auth")

# Update routes that use the old implementation
print("Replit Auth updated to use the new implementation.")
print("Please check all imports in your routes to use:")
print("  from replit_auth_new import require_auth as require_login")
print("  from replit_auth_new import replit")
print("Instead of:")
print("  from replit_auth import require_login")
print("  from replit_auth import replit")

if __name__ == "__main__":
    print("To apply these changes, restart your application server.")