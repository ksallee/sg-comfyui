"""What the executing graph says about the image: the words, the models, and whose branch."""
import graphs

from comfyui_sg import provenance


def test_a_zeroed_out_negative_reports_no_words():
    """ConditioningZeroOut erases what it is handed, so the text behind it reached nothing."""
    positive, negative = provenance.directing_text(graphs.sdxl_zero_out(),
                                                   set(graphs.sdxl_zero_out()))
    assert positive == ["a red car", "studio light"]
    assert negative == []


def test_two_tokenisers_on_one_encoder_are_both_kept():
    prov = provenance.extract(graphs.sdxl_zero_out())
    assert prov["prompts"]["positive"] == ["a red car", "studio light"]
    assert prov["samplers"][0]["negative"] == []


def test_the_flux_encoders_texts_are_kept_apart():
    prov = provenance.extract(graphs.flux_dual_encoder())
    assert prov["prompts"]["positive"] == ["a lighthouse", "a lighthouse in a storm at dusk"]
    assert [m["name"] for m in prov["models"]] == ["flux1-dev.safetensors"]
    assert prov["loras"] == [{"node_id": "3", "name": "film_grain.safetensors",
                              "strength_model": 0.6}]


def test_each_publish_node_describes_its_own_branch():
    prompt = graphs.two_branches()
    first = provenance.extract(prompt, node_id="20")
    second = provenance.extract(prompt, node_id="30")
    assert first["prompts"]["positive"] == ["a wide desert"]
    assert second["prompts"]["positive"] == ["a snowy street"]
    assert [s["seed"] for s in first["samplers"]] == [111]
    assert [s["seed"] for s in second["samplers"]] == [222]


def test_a_shared_node_is_an_ancestor_of_both_branches():
    prompt = graphs.two_branches()
    assert provenance.ancestors(prompt, "20") == {"20", "12", "11", "10", "1"}
    assert "1" in provenance.ancestors(prompt, "30")
    assert "11" not in provenance.ancestors(prompt, "30")


def test_words_taken_as_a_widget_are_a_prompt():
    prov = provenance.extract(graphs.prompt_widget_no_sampler())
    assert prov["prompts"] == {"positive": ["the camera pushes in"],
                               "negative": ["text, watermark"]}


def test_a_graph_with_no_sampler_still_says_what_it_was_told_to_make():
    prov = provenance.extract(graphs.prompt_widget_no_sampler())
    assert prov["samplers"] == []
    assert prov["node_count"] == 3


def test_the_two_roles_of_a_controlnet_never_merge():
    prov = provenance.extract(graphs.controlnet_advanced())
    assert prov["prompts"]["positive"] == ["a marble statue"]
    assert prov["prompts"]["negative"] == ["blurry, low contrast"]


def test_a_pinned_version_is_read_out_of_the_graph():
    assert provenance.loaded_versions(graphs.loaded_and_published(1042), "3") == [1042]
    assert provenance.loaded_versions(graphs.loaded_and_published(0), "3") == []


def test_the_workflow_is_absent_unless_the_client_sent_one():
    assert provenance.workflow(None) is None
    assert provenance.workflow({"workflow": {"nodes": []}}) == {"nodes": []}
    assert provenance.extract({}, None)["workflow_attached"] is False
