"""Suite de tests unitarios para las capacidades integradas de LinkedIn."""

import pytest
from src.linkedin.url_parser import parse_linkedin_url, build_parent_comment_urn


def test_parse_linkedin_url_standard_post():
    url = "https://www.linkedin.com/posts/johndoe_awesome-tech-activity-7123456789012345678-abcd"
    parsed = parse_linkedin_url(url)
    assert parsed["url_type"] == "post"
    assert parsed["post_activity_id"] == "7123456789012345678"
    assert parsed["post_urn"] == "urn:li:activity:7123456789012345678"
    assert parsed["comment_id"] is None


def test_parse_linkedin_url_comment():
    url = (
        "https://www.linkedin.com/feed/update/urn:li:activity:7123456789012345678"
        "?commentUrn=urn%3Ali%3Acomment%3A%28activity%3A7123456789012345678%2C7987654321098765432%29"
    )
    parsed = parse_linkedin_url(url)
    assert parsed["url_type"] == "comment"
    assert parsed["post_activity_id"] == "7123456789012345678"
    assert parsed["post_urn"] == "urn:li:activity:7123456789012345678"
    assert parsed["comment_id"] == "7987654321098765432"
    assert parsed["comment_urn"] == "urn:li:comment:(urn:li:activity:7123456789012345678,7987654321098765432)"


def test_parse_linkedin_url_share_and_ugcpost():
    share_url = "https://www.linkedin.com/posts/founder_tech-share-7123456789012345678-xyz"
    parsed_share = parse_linkedin_url(share_url)
    assert parsed_share["url_type"] == "post"
    assert parsed_share["post_urn"] == "urn:li:share:7123456789012345678"

    ugc_url = "https://www.linkedin.com/posts/founder_tech-ugcPost-7123456789012345678-xyz"
    parsed_ugc = parse_linkedin_url(ugc_url)
    assert parsed_ugc["url_type"] == "post"
    assert parsed_ugc["post_urn"] == "urn:li:ugcPost:7123456789012345678"


def test_parse_linkedin_url_invalid_or_empty():
    assert parse_linkedin_url("")["url_type"] == "unknown"
    assert parse_linkedin_url("https://example.com/not-linkedin")["url_type"] == "unknown"


def test_build_parent_comment_urn():
    urn = build_parent_comment_urn("urn:li:activity:123", "456")
    assert urn == "urn:li:comment:(urn:li:activity:123,456)"
def test_approval_gate_lifecycle():
    from src.linkedin.approval import ApprovalGate, ApprovalStatus
    gate = ApprovalGate()
    status = gate.request_approval("draft_1", "Sample content")
    assert status == ApprovalStatus.PENDING
    assert not gate.is_approved("draft_1")

    gate.confirm("draft_1")
    assert gate.is_approved("draft_1")
    assert gate.get_status("draft_1") == ApprovalStatus.APPROVED
def test_approval_gate_triangulation():
    from src.linkedin.approval import ApprovalGate, ApprovalStatus
    gate = ApprovalGate()
    gate.request_approval("draft_rej", "Content to reject")
    gate.reject("draft_rej")
    assert gate.get_status("draft_rej") == ApprovalStatus.REJECTED
    assert not gate.is_approved("draft_rej")

    with pytest.raises(KeyError):
        gate.confirm("unknown_draft")

    card = gate.render_approval_card(
        kind="post",
        preview_text="Line 1\nLine 2",
        target_url="https://linkedin.com/posts/test",
    )
    assert "Draft ready for approval — post" in card
    assert "> Line 1" in card
    assert "https://linkedin.com/posts/test" in card
def test_hooks_registry():
    from src.linkedin.hooks import HOOK_FORMULAS, FOUNDER_ANGLES, get_hook_formula, get_founder_angle
    assert len(HOOK_FORMULAS) == 20
    assert len(FOUNDER_ANGLES) == 10

    f1 = get_hook_formula("F1")
    assert f1["name"] == "Platform Risk Anaphora"
    assert "Platform1" in f1["template"]

    a1 = get_founder_angle("A1")
    assert a1["name"] == "Reprice the Category"
    assert a1["best_fit_formula"] in ("F10", "F2")

    assert get_hook_formula("INVALID") is None
    assert get_founder_angle("INVALID") is None
def test_hooks_registry_triangulation():
    from src.linkedin.hooks import HOOK_FORMULAS, FOUNDER_ANGLES, get_hook_formula, get_founder_angle
    for code, item in HOOK_FORMULAS.items():
        assert item["name"], f"Hook {code} missing name"
        assert item["template"], f"Hook {code} missing template"
        assert item["goal"] in ("comments", "reposts", "likes", "saves")
        assert get_hook_formula(code) is not None

    for code, item in FOUNDER_ANGLES.items():
        assert item["name"], f"Angle {code} missing name"
        assert item["template"], f"Angle {code} missing template"
        assert item["goal"] in ("comments", "reposts", "likes", "saves")
        assert get_founder_angle(code) is not None
def test_backend_selector_draft_fallback():
    from src.linkedin.backends import BackendSelector
    selector = BackendSelector(env={})
    assert selector.active_backend == "draft"
    res = selector.publish("Draft post text")
    assert res["status"] == "draft"
    assert res["backend"] == "draft"
    assert "Draft post text" in res["content"]


def test_backend_selector_publora_mocked():
    from unittest.mock import MagicMock
    from src.linkedin.backends import BackendSelector
    from src.linkedin.clients.publora import PubloraClient

    mock_client = MagicMock(spec=PubloraClient)
    mock_client.create_post.return_value = {"id": "pub_123", "status": "scheduled"}

    selector = BackendSelector(
        env={"PUBLORA_API_KEY": "fake_key", "LINKEDIN_PLATFORM_ID": "plat_123"},
        publora_client=mock_client,
    )
    assert selector.active_backend == "publora"
    res = selector.publish("Live post text")
    assert res["status"] == "published"
    assert res["id"] == "pub_123"
    mock_client.create_post.assert_called_once_with(text="Live post text", media_urls=None)
def test_backend_selector_pixfaro_mocked():
    from unittest.mock import MagicMock
    from src.linkedin.backends import BackendSelector
    from src.linkedin.clients.pixfaro import PixfaroClient

    mock_client = MagicMock(spec=PixfaroClient)
    mock_client.create_post.return_value = {"id": "pix_456", "success": True}

    selector = BackendSelector(
        env={"PIXFARO_API_KEY": "fake_pix", "PIXFARO_ACCOUNT_ID": "acc_789"},
        pixfaro_client=mock_client,
    )
    assert selector.active_backend == "pixfaro"
    res = selector.publish("Pixfaro text", media_urls=["https://img.jpg"])
    assert res["status"] == "published"
    assert res["backend"] == "pixfaro"
    assert res["id"] == "pix_456"
    mock_client.create_post.assert_called_once_with(text="Pixfaro text", media_urls=["https://img.jpg"])


def test_clients_missing_credentials_raise():
    from src.linkedin.clients.publora import PubloraClient
    from src.linkedin.clients.pixfaro import PixfaroClient

    pub = PubloraClient(api_key="", platform_id="")
    with pytest.raises(ValueError):
        pub.create_post("fail")

    pix = PixfaroClient(api_key="", account_id="")
    with pytest.raises(ValueError):
        pix.create_post("fail")
def test_post_generator_hook_instruction():
    from src.post_generator import build_hook_instruction
    inst_f1 = build_hook_instruction("F1", language="es")
    assert "F1 - Platform Risk Anaphora" in inst_f1
    assert "Platform1" in inst_f1

    inst_a1 = build_hook_instruction("A1", language="en")
    assert "A1 - Reprice the Category" in inst_a1

    assert build_hook_instruction(None) == ""
    assert build_hook_instruction("INVALID") == ""
def test_generate_single_project_post_with_hook_mocked(monkeypatch):
    from unittest.mock import MagicMock
    from src import post_generator

    mock_llm = MagicMock(return_value=("=== LINKEDIN_POST ===\nF1 Content\n=== PRIMER_COMENTARIO ===\nComment\n=== GUION_CARRUSEL_PDF ===\nSlides", "mock_model"))
    monkeypatch.setattr(post_generator, "generate_llm_text", mock_llm)
    monkeypatch.setattr(post_generator, "process_and_enforce_humanizer_qc", lambda pkg, **kw: (pkg, {}))
    monkeypatch.setattr(post_generator, "_run_quality_gate", lambda pkg, *args, **kw: pkg)

    res = post_generator.generate_single_project_post(
        repo_name="my-repo",
        commits=["feat: add feature"],
        hook_formula="F1",
    )
    assert res is not None
    called_prompt = mock_llm.call_args[1]["prompt"]
    assert "F1 - Platform Risk Anaphora" in called_prompt
def test_audit_emoji_density():
    from src.humanizer_qc import audit_emoji_density

    passed, count, msg = audit_emoji_density("Architecture with zero emojis.")
    assert passed is True
    assert count == 0

    passed, count, msg = audit_emoji_density("🚀 Clean 🛠️ Stack 💡", max_emojis=3)
    assert passed is True
    assert count == 3

    passed, count, msg = audit_emoji_density("🚀 🛠️ 💡 🔥 ✨", max_emojis=3)
    assert passed is False
    assert count == 5
    assert "Excessive emoji density" in msg


def test_audit_algorithm_heuristics():
    from src.humanizer_qc import audit_algorithm_heuristics

    good_text = (
        "Opening line explaining architecture.\n\n"
        "Second paragraph with technical depth.\n\n"
        "Check repo at https://github.com/my-repo"
    )
    passed, issues = audit_algorithm_heuristics(good_text)
    assert passed is True
    assert len(issues) == 0

    bad_opening_link = (
        "Check out https://example.com/blog now!\n"
        "This is an external link in opening line."
    )
    passed, issues = audit_algorithm_heuristics(bad_opening_link)
    assert passed is False
    assert any("opening lines" in i.lower() for i in issues)
def test_audit_algorithm_heuristics_monolithic_block():
    from src.humanizer_qc import audit_algorithm_heuristics

    monolithic = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6\nLine 7"
    passed, issues = audit_algorithm_heuristics(monolithic)
    assert passed is False
    assert any("Monolithic block" in i for i in issues)

    spaced = "Line 1\nLine 2\n\nLine 3\nLine 4\n\nLine 5\nLine 6"
    passed, issues = audit_algorithm_heuristics(spaced)
    assert passed is True
    assert len(issues) == 0


def test_qc_empty_text():
    from src.humanizer_qc import audit_emoji_density, audit_algorithm_heuristics

    passed, count, _ = audit_emoji_density("")
    assert passed is True
    assert count == 0

    passed, issues = audit_algorithm_heuristics("")
    assert passed is True
    assert len(issues) == 0
def test_skills_and_references_ingestion():
    from pathlib import Path

    expected_skills = [
        "linkedin-comment-drafter",
        "linkedin-content-planner",
        "linkedin-employee-advocacy",
        "linkedin-engager-analytics",
        "linkedin-hook-extractor",
        "linkedin-humanizer",
        "linkedin-post-writer",
        "linkedin-profile-optimizer",
        "linkedin-reply-handler",
        "linkedin-repurposer",
        "linkedin-thread-monitor",
    ]
    skills_root = Path(".agents/skills")
    for s in expected_skills:
        skill_file = skills_root / s / "SKILL.md"
        assert skill_file.is_file(), f"Missing skill file: {skill_file}"

    expected_refs = [
        "algorithm-heuristics.md",
        "engagement-metrics-taxonomy.md",
        "founder-topics.md",
        "hook-formulas.md",
        "industry-benchmarks.md",
        "untrusted-content.md",
        "voice-profile.md",
        "voice-rules.md",
    ]
    refs_root = Path("docs/references")
    for r in expected_refs:
        ref_file = refs_root / r
        assert ref_file.is_file(), f"Missing reference file: {ref_file}"


def test_publora_create_post_with_pdf_carousel(monkeypatch):
    from unittest.mock import MagicMock
    from src.linkedin.clients.publora import PubloraClient

    client = PubloraClient(api_key='dummy_key', platform_id='dummy_plat')

    post_res = MagicMock(ok=True, status_code=200)
    post_res.json.return_value = {'postGroupId': 'grp_123'}

    upload_res = MagicMock(ok=True, status_code=200)
    upload_res.json.return_value = {'uploadUrl': 'https://s3.aws.com/upload', 'mediaId': 'med_456'}

    complete_res = MagicMock(ok=True, status_code=200)
    complete_res.json.return_value = {'success': True}

    update_res = MagicMock(ok=True, status_code=200)
    update_res.json.return_value = {'success': True}

    client.session.post = MagicMock(side_effect=[post_res, upload_res, complete_res])
    client.session.put = MagicMock(return_value=update_res)

    mock_s3_put = MagicMock(return_value=MagicMock(ok=True, status_code=200))
    monkeypatch.setattr('requests.put', mock_s3_put)

    res = client.create_post(text='Hello', pdf_bytes=b'%PDF-test')

    assert res['postGroupId'] == 'grp_123'
    client.session.post.assert_any_call(
        'https://api.publora.com/api/v1/complete-media/med_456',
        json={'postGroupId': 'grp_123'},
        headers={'x-publora-key': 'dummy_key', 'Authorization': 'Bearer dummy_key', 'Content-Type': 'application/json'},
        timeout=15,
    )
