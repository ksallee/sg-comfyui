"""The sidebar's REST relay: which requests pass, and what crosses with them."""
import pytest

from comfyui_sg import relay


@pytest.mark.parametrize("method, path", [
    ("GET", "/schema"),
    ("GET", "/schema/Version/fields"),
    ("GET", "/schema/Version/fields/sg_status_list"),
    ("GET", "/entity/versions/42"),
    ("GET", "/entity/statuses"),
    ("POST", "/entity/versions/_search"),
    ("POST", "/entity/icons/_search"),
    ("POST", "/entity/_text_search"),
])
def test_reads_pass(method, path):
    assert relay.allowed(method, path)


@pytest.mark.parametrize("method, path", [
    ("POST", "/entity/versions"),                          # create
    ("PUT", "/entity/versions/42"),                        # update
    ("DELETE", "/entity/versions/42"),                     # retire
    ("POST", "/entity/versions/42"),                       # revive
    ("POST", "/entity/_batch"),                            # batch writes
    ("GET", "/entity/versions/42/sg_uploaded_movie/_upload"),  # an upload ticket
    ("POST", "/auth/access_token"),
    ("GET", "/entity/versions/42/../../auth/access_token"),
    ("GET", "/entity/versions/_search"),                   # search is a POST
    ("POST", "/schema/Version/fields"),                    # a field create
    ("OPTIONS", "/schema"),
])
def test_everything_else_is_refused(method, path):
    assert not relay.allowed(method, path)


def test_only_the_content_type_crosses():
    headers = {
        "Content-Type": "application/vnd+shotgun.api3_hash+json",
        "Authorization": "Bearer relay",
        "Cookie": "comfy=1",
    }
    assert relay.forward_headers(headers) == {
        "Content-Type": "application/vnd+shotgun.api3_hash+json"}


def test_no_content_type_sends_none():
    assert relay.forward_headers({"Accept": "application/json"}) == {}


def test_refusal_is_a_json_api_error():
    body = relay.refusal("PUT", "/entity/versions/42")
    assert body["errors"][0]["status"] == 403
    assert "PUT /entity/versions/42" in body["errors"][0]["detail"]
