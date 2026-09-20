"""Database seed script for development and testing."""

import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path so app can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.consent import Consent
from app.models.course import Course
from app.models.topic import Topic
from app.models.user import User, UserRole
from app.services.auth_service import hash_password


async def seed_database() -> None:
    """Populate database with sample teacher, student, course, topics, and consent."""
    print("[*] Seeding database...")
    async with AsyncSessionLocal() as session:
        # 1. Create Teacher
        teacher_email = "teacher@viva.edu"
        result = await session.execute(select(User).where(User.email == teacher_email))
        teacher = result.scalar_one_or_none()
        if not teacher:
            teacher = User(
                email=teacher_email,
                hashed_password=hash_password("teacher123"),
                full_name="Dr. Alan Turing",
                role=UserRole.TEACHER,
            )
            session.add(teacher)
            await session.commit()
            await session.refresh(teacher)
            print(f"[+] Created Teacher: {teacher.email} (id={teacher.id})")
        else:
            print(f"[-] Teacher already exists: {teacher.email}")

        # 2. Create Student
        student_email = "student@viva.edu"
        result = await session.execute(select(User).where(User.email == student_email))
        student = result.scalar_one_or_none()
        if not student:
            student = User(
                email=student_email,
                hashed_password=hash_password("student123"),
                full_name="Ada Lovelace",
                role=UserRole.STUDENT,
            )
            session.add(student)
            await session.commit()
            await session.refresh(student)
            print(f"[+] Created Student: {student.email} (id={student.id})")
        else:
            print(f"[-] Student already exists: {student.email}")

        # 3. Create Course
        course_code = "CS201"
        result = await session.execute(select(Course).where(Course.code == course_code))
        course = result.scalar_one_or_none()
        if not course:
            course = Course(
                teacher_id=teacher.id,
                name="Data Structures & Algorithms",
                code=course_code,
                description="Core computer science course covering linear and non-linear data structures, searching, and sorting.",
            )
            session.add(course)
            await session.commit()
            await session.refresh(course)
            print(f"[+] Created Course: {course.name} ({course.code})")
        else:
            print(f"[-] Course already exists: {course.code}")

        # 4. Create Topics
        topics_data = [
            ("Arrays, Stacks & Queues", 1),
            ("Trees & Binary Search Trees", 2),
            ("Graph Traversal Algorithms", 3),
            ("Sorting & Dynamic Programming", 4),
        ]
        for name, order in topics_data:
            t_res = await session.execute(
                select(Topic).where(Topic.course_id == course.id, Topic.name == name)
            )
            if not t_res.scalar_one_or_none():
                topic = Topic(
                    course_id=course.id,
                    name=name,
                    sort_order=order,
                )
                session.add(topic)
                print(f"  [+] Added Topic: {name}")
        await session.commit()

        # 5. Create Initial Student Consent
        c_res = await session.execute(select(Consent).where(Consent.user_id == student.id))
        if not c_res.scalar_one_or_none():
            consent = Consent(
                user_id=student.id,
                audio_retention_consent=True,
                transcript_consent=True,
            )
            session.add(consent)
            await session.commit()
            print("[+] Added baseline student consent record")

        print("[OK] Seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_database())
