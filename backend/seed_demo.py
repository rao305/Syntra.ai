"""Seed script for demo organization and data.

Usage:
    python seed_demo.py
"""
import asyncio
import sys
from datetime import datetime

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.org import Org
from app.models.user import User
from app.models.thread import Thread
from app.models.message import Message, MessageRole


async def seed_demo_data():
    """Create demo organization, user, and thread for testing."""

    async with AsyncSessionLocal() as session:
        try:
            # Check if demo org already exists
            stmt = select(Org).where(Org.slug == "demo")
            result = await session.execute(stmt)
            existing_org = result.scalar_one_or_none()

            if existing_org:
                print(f"✓ Demo org already exists: {existing_org.id}")
                org_id = existing_org.id
            else:
                # Create demo organization
                demo_org = Org(
                    id="org_demo",
                    name="Demo Organization",
                    slug="demo",
                    subscription_status="trial",
                    seats_licensed=10,
                    seats_used=1
                )
                session.add(demo_org)
                await session.flush()
                org_id = demo_org.id
                print(f"✓ Created demo org: {org_id}")

            # Check if demo user exists
            stmt = select(User).where(User.email == "demo@example.com")
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print(f"✓ Demo user already exists: {existing_user.id}")
                user_id = existing_user.id
            else:
                # Create demo user
                demo_user = User(
                    email="demo@example.com",
                    name="Demo User",
                    org_id=org_id,
                    role="admin",
                    email_verified=datetime.utcnow()
                )
                session.add(demo_user)
                await session.flush()
                user_id = demo_user.id
                print(f"✓ Created demo user: {user_id}")

            # Create demo thread
            demo_thread = Thread(
                org_id=org_id,
                creator_id=user_id,
                title="Welcome Thread",
                description="Demo thread for testing"
            )
            session.add(demo_thread)
            await session.flush()
            thread_id = demo_thread.id
            print(f"✓ Created demo thread: {thread_id}")

            # Create initial message
            welcome_message = Message(
                thread_id=thread_id,
                user_id=user_id,
                role=MessageRole.SYSTEM,
                content="Welcome to the Cross-LLM Thread Hub! This is a demo thread.",
                sequence=0
            )
            session.add(welcome_message)

            # Commit all changes
            await session.commit()

            print("\n" + "="*60)
            print("SEED DATA CREATED SUCCESSFULLY")
            print("="*60)
            print(f"Organization ID: {org_id}")
            print(f"User ID: {user_id}")
            print(f"Thread ID: {thread_id}")
            print("="*60)
            print("\nYou can now:")
            print(f"1. Visit http://localhost:3000/settings/providers")
            print(f"2. Add provider API keys for org: {org_id}")
            print(f"3. Test connections")
            print(f"4. Visit http://localhost:3000/threads to chat")
            print("="*60)

            return {
                "org_id": org_id,
                "user_id": user_id,
                "thread_id": thread_id
            }

        except Exception as e:
            print(f"✗ Error seeding data: {str(e)}", file=sys.stderr)
            await session.rollback()
            raise


if __name__ == "__main__":
    print("Seeding demo data...")
    result = asyncio.run(seed_demo_data())
    print("\nSeed complete!")
