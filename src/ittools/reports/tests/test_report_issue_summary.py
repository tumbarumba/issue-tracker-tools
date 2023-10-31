from ittools.reports import report_issue_summary as ris


def test_projects_without_labels_are_unplanned():
    assert ris._project_for([]) == "Unplanned"


def test_project_label_excludes_teams():
    assert ris._project_for(["TeamTBD"]) == "Unplanned"
    assert ris._project_for(["TeamTBD", "CBG"]) == "CBG"


def test_project_excludes_milestones():
    assert ris._project_for(["CBG_GTM"]) == "CBG"
