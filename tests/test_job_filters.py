from Assets.scraper import filter_jobs_for_preferences


def test_filter_jobs_by_notice_period_and_wfh_and_location():
    jobs = [
        {
            "title": "Python Developer",
            "location": {"display_name": "Bangalore, India"},
            "description": "Work from home available. Candidate can join in 15 days.",
        },
        {
            "title": "Data Analyst",
            "location": {"display_name": "Pune, India"},
            "description": "Requires 2 months notice period and office-first role.",
        },
        {
            "title": "Senior Engineer",
            "location": {"display_name": "Hyderabad, India"},
            "description": "Remote friendly, immediate joiner preferred.",
        },
    ]

    filtered = filter_jobs_for_preferences(
        jobs,
        notice_period_days=30,
        work_from_home=True,
        preferred_locations=["Bangalore", "Hyderabad"],
    )

    assert len(filtered) == 2
    assert filtered[0]["title"] == "Python Developer"
    assert filtered[1]["title"] == "Senior Engineer"


def test_filter_jobs_ignores_unrelated_location_when_location_not_specified():
    jobs = [
        {"title": "ML Engineer", "location": {"display_name": "Delhi, India"}, "description": "Remote role with 30 day notice."},
        {"title": "Backend Engineer", "location": {"display_name": "Mumbai, India"}, "description": "Office role with 90 day notice."},
    ]

    filtered = filter_jobs_for_preferences(jobs, notice_period_days=45, work_from_home=True)

    assert len(filtered) == 1
    assert filtered[0]["title"] == "ML Engineer"
