import click
from flask.cli import with_appcontext
from flask import current_app

from app import db
from app.models import User, Subscription, UsageQuota
from app.nlp.nlp_exercises import initialize_default_exercises

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Initialize the database with required tables."""
    click.echo('Creating database tables...')
    db.create_all()
    click.echo('Database tables created.')

@click.command('init-exercises')
@with_appcontext
def init_exercises_command():
    """Initialize the database with default NLP exercises."""
    click.echo('Creating default NLP exercises...')
    initialize_default_exercises()
    click.echo('Default NLP exercises created.')

@click.command('create-admin')
@click.argument('email')
@click.argument('password')
@with_appcontext
def create_admin_command(email, password):
    """Create an admin user with the given email and password."""
    try:
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        
        if user:
            click.echo(f'User with email {email} already exists.')
            return
            
        # Create new user
        import uuid
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            first_name='Admin',
            last_name='User',
            auth_provider='email',
            email_verified=True
        )
        
        # Set password
        user.set_password(password)
        
        # Save to database
        db.session.add(user)
        db.session.commit()
        
        click.echo(f'Admin user created with email: {email}')
        
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error creating admin user: {str(e)}')

@click.command('create-subscription')
@click.argument('user_id')
@click.argument('plan_name')
@with_appcontext
def create_subscription_command(user_id, plan_name):
    """Create a subscription for a user with the given plan."""
    try:
        # Check if user exists
        user = User.query.get(user_id)
        
        if not user:
            click.echo(f'User with ID {user_id} not found.')
            return
            
        # Check if plan name is valid
        valid_plans = ['free', 'premium', 'professional']
        if plan_name not in valid_plans:
            click.echo(f'Invalid plan name. Must be one of: {", ".join(valid_plans)}')
            return
            
        # Check if subscription exists
        subscription = Subscription.query.filter_by(user_id=user_id).first()
        
        if subscription:
            # Update existing subscription
            subscription.plan_name = plan_name
            subscription.status = 'active'
            db.session.commit()
            click.echo(f'Updated subscription for user {user_id} to {plan_name} plan.')
        else:
            # Create new subscription
            subscription = Subscription(
                user_id=user_id,
                plan_name=plan_name,
                status='active'
            )
            db.session.add(subscription)
            db.session.commit()
            click.echo(f'Created {plan_name} subscription for user {user_id}.')
            
    except Exception as e:
        db.session.rollback()
        click.echo(f'Error creating subscription: {str(e)}')

def register_commands(app):
    """Register Flask CLI commands."""
    app.cli.add_command(init_db_command)
    app.cli.add_command(init_exercises_command)
    app.cli.add_command(create_admin_command)
    app.cli.add_command(create_subscription_command)