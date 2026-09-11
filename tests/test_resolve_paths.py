"""What a template token reads off the site: a dotted path from attributes, a bare linked field
from relationships (probe 003)."""
from comfyui_sg import site


class Answer:
    ok = True

    def __init__(self, attributes, relationships):
        self._body = {"data": {"id": 46715, "attributes": attributes,
                               "relationships": relationships}}

    def json(self):
        return self._body


class Client:
    def __init__(self):
        self.calls = []

    def get(self, path, params=None):
        self.calls.append((path, params))
        return Answer({"content": "Roto", "step.Step.short_name": "RTO"},
                      {"step": {"data": {"type": "Step", "id": 134, "name": "Roto"}}})


def test_a_bare_linked_field_is_the_link_name(monkeypatch):
    c = Client()
    monkeypatch.setattr(site, "client", lambda: c)
    monkeypatch.setattr(site, "_cache", {})
    got = site.resolve_paths(["sg_task", "sg_task.Task.step", "sg_task.Task.step.Step.short_name"],
                             1180, "Shot", 7514, 46715)
    assert got == {"sg_task": "Roto", "sg_task.Task.step": "Roto",
                   "sg_task.Task.step.Step.short_name": "RTO"}
    assert c.calls == [("/entity/tasks/46715",
                        {"fields": "content,step,step.Step.short_name"})]


def test_forget_with_no_prefix_drops_everything(monkeypatch):
    monkeypatch.setattr(site, "_cache", {("paths", "Task", 1, ("step",)): (0, {}),
                                         ("tasks", "Shot", 7514): (0, [])})
    site.forget("tasks")
    assert list(site._cache) == [("paths", "Task", 1, ("step",))]
    site.forget()
    assert site._cache == {}
