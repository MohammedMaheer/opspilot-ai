from core.rules import infer_category, infer_priority, safety_scan


def test_fire_is_p0():
    text = "There are sparks and a burning smell from a socket"
    hits = safety_scan(text)
    assert hits
    assert infer_priority(text, "one person", hits) == "P0"


def test_lift_entrapment_is_safety_event():
    hits = safety_scan("Two people are stuck inside lift L2 and the alarm is sounding")
    assert any(x.rule_id == "SAFE-004" for x in hits)


def test_hvac_category():
    assert infer_category("The AC is not cooling the meeting room") == "hvac"


def test_normal_single_user_issue_is_p3():
    text = "One access card is not working at the clubhouse"
    assert infer_priority(text, "one person", safety_scan(text)) == "P3"
