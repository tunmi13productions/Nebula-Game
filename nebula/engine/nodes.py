"""Scene graph: nodes with a position, parent and children, and keyed actions, like SKNode."""


class Node:
    def __init__(self, name=None, position=(0.0, 0.0), size=(0.0, 0.0)):
        self.name = name
        self.position = position
        self.size = size
        self.anchor = (0.5, 0.5)
        self.z = 0.0
        self.scale = 1.0
        self.alpha = 1.0
        self.rotation = 0.0
        self.hidden = False
        self.paused = False
        self.parent = None
        self.children = []
        self.physics = None
        self._actions = []   # (key, runner, completion)

    @property
    def width(self):
        return self.size[0]

    @width.setter
    def width(self, w):
        self.size = (w, self.size[1])

    # tree

    def add_child(self, node):
        if node.parent is not None:
            node.remove_from_parent()
        node.parent = self
        self.children.append(node)

    def remove_from_parent(self):
        if self.parent is not None:
            self.parent.children.remove(self)
            self.parent = None

    def remove_all_children(self):
        for c in list(self.children):
            c.remove_from_parent()

    @property
    def scene(self):
        n = self
        while n.parent is not None:
            n = n.parent
        return n if isinstance(n, Scene) else None

    def walk(self):
        yield self
        for c in list(self.children):
            yield from c.walk()

    # actions

    def run(self, action, key=None, completion=None):
        """runAction, runAction:withKey: (replacing any action with that key) and runAction:completion:."""
        if key is not None:
            self.remove_action(key)
        self._actions.append((key, action.runner(self), completion))

    def remove_action(self, key):
        self._actions = [a for a in self._actions if a[0] != key]

    def has_action(self, key):
        return any(a[0] == key for a in self._actions)

    def remove_all_actions(self):
        self._actions = []

    def update_actions(self, dt):
        if self.paused:
            return
        for entry in list(self._actions):
            if entry not in self._actions:
                continue   # removed by an earlier action this frame
            key, runner, completion = entry
            if runner.update(dt) is not None:
                if entry in self._actions:
                    self._actions.remove(entry)
                if completion is not None:
                    completion()


class Scene(Node):
    """Root node. Each frame: on_update(dt), then every node's actions are evaluated, then physics."""

    def __init__(self, width=320.0, height=568.0):
        super().__init__(name='scene', position=(0.0, 0.0), size=(width, height))
        self.time = 0.0
        self.physics_world = None

    @property
    def frame(self):
        return (0.0, 0.0, self.size[0], self.size[1])

    def on_update(self, dt):
        """Override for per-frame logic, the equivalent of SKScene update:."""

    def did_begin_contact(self, a, b):
        """Override: SKPhysicsContactDelegate didBeginContact:. a and b are physics Body objects."""

    def did_end_contact(self, a, b):
        """Override: SKPhysicsContactDelegate didEndContact:."""

    def step(self, dt):
        if self.paused:
            return
        self.time += dt
        self.on_update(dt)
        for node in list(self.walk()):
            if node is self or node.scene is self:
                if not _ancestor_paused(node):
                    node.update_actions(dt)
        if self.physics_world is not None:
            self.physics_world.simulate(self)


def _ancestor_paused(node):
    n = node.parent
    while n is not None:
        if n.paused:
            return True
        n = n.parent
    return False
