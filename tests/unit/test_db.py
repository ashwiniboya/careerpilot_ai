import datetime
from database.models import User, UserProfile, Resume, CareerHistory, SkillTracking
from src.api.auth import _hash_password, _verify_password

def test_create_user_and_profile(db_session):
    # 1. Create a user
    new_user = User(
        email="test_user@example.com",
        hashed_password="hashed_password_xyz",
        full_name="Alice Candidate"
    )
    db_session.add(new_user)
    db_session.commit()
    db_session.refresh(new_user)

    assert new_user.id is not None
    assert new_user.email == "test_user@example.com"
    assert len(new_user.profiles) == 0

    # 2. Create a profile linked to the user
    new_profile = UserProfile(
        user_id=new_user.id,
        target_role="Machine Learning Engineer",
        target_industry="AI / Tech",
        experience_level="Senior",
        target_salary=150000.0,
        preferences={"work_setting": "Remote", "communication": "direct"}
    )
    db_session.add(new_profile)
    db_session.commit()
    db_session.refresh(new_user)

    assert len(new_user.profiles) == 1
    assert new_user.profiles[0].target_role == "Machine Learning Engineer"
    assert new_user.profiles[0].preferences["work_setting"] == "Remote"


def test_resume_and_career_history(db_session):
    # Create user
    user = User(email="bob@example.com", hashed_password="pwd")
    db_session.add(user)
    db_session.commit()

    # Add Career History
    job = CareerHistory(
        user_id=user.id,
        company="Startup Co",
        role="Backend Dev",
        description="Built REST APIs and microservices in Go.",
        start_date=datetime.date(2023, 1, 1),
        end_date=datetime.date(2025, 2, 28),
        skills_used=["Go", "SQL", "Docker"]
    )
    db_session.add(job)

    # Add Resume
    resume = Resume(
        user_id=user.id,
        original_filename="bob_resume.md",
        file_type="markdown",
        content_raw="Bob is a Go developer.",
        content_markdown="## Bob\nGo Dev.",
        parsed_data={"skills": ["Go", "SQL", "Docker"]},
        last_ats_score=78.5
    )
    db_session.add(resume)
    db_session.commit()

    # Query and Verify
    db_session.refresh(user)
    assert len(user.career_history) == 1
    assert user.career_history[0].company == "Startup Co"
    assert "Docker" in user.career_history[0].skills_used

    assert len(user.resumes) == 1
    assert user.resumes[0].original_filename == "bob_resume.md"
    assert user.resumes[0].last_ats_score == 78.5


def test_skills_assessment(db_session):
    # Create user
    user = User(email="charlie@example.com", hashed_password="pwd")
    db_session.add(user)
    db_session.commit()

    # Add skills
    skill1 = SkillTracking(user_id=user.id, skill_name="Python", category="Technical", current_proficiency=3, target_proficiency=5)
    skill2 = SkillTracking(user_id=user.id, skill_name="System Design", category="Domain", current_proficiency=2, target_proficiency=4)
    db_session.add_all([skill1, skill2])
    db_session.commit()

    db_session.refresh(user)
    assert len(user.skills) == 2
    skills_dict = {s.skill_name: s.current_proficiency for s in user.skills}
    assert skills_dict["Python"] == 3
    assert skills_dict["System Design"] == 2


def test_password_hashing_and_verification_work():
    password = "secret123"
    hashed = _hash_password(password)

    assert hashed != password
    assert _verify_password(password, hashed) is True
    assert _verify_password("wrong-password", hashed) is False
