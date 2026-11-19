"""Drawing UIKit screens with the scene renderer. Visual only.

Each screen keeps a Scene (`view`) of 320 by 568 points with a black background. UIKit frames are given with
the origin at the top left, as the original code set them, and converted to SpriteKit-style positions here.
"""
from ..engine.nodes import Node, Scene

W, H = 320.0, 568.0


def new_view():
    view = Scene(W, H)
    view.background = (0.0, 0.0, 0.0)
    return view


def image(texture, x, y, w, h, z=0.0):
    """A UIImageView at frame (x, y, w, h), top-left origin."""
    n = Node(name=texture, size=(w, h), position=(x + w / 2, H - (y + h / 2)))
    n.texture, n.z = texture, z
    return n


def fill(color, x, y, w, h, z=0.0):
    n = Node(name='fill', size=(w, h), position=(x + w / 2, H - (y + h / 2)))
    n.color, n.z = color, z
    return n


def text(value, x, y, w, h, size, font='Futura', color=(1.0, 1.0, 1.0), z=0.0):
    """A centred UILabel in frame (x, y, w, h): the text is centred vertically in the frame."""
    n = Node(name='label', position=(x + w / 2, H - (y + h / 2) - size * 0.35))
    n.text, n.font_size, n.font_name, n.font_color, n.z = value, size, font, color, z
    return n


def localized(name, strings, suffix=''):
    """Global checkImageTelaJPG: "_en" in any language but Portuguese, plus "_4" for some images on 4-inch
    screens (the doors)."""
    return name + ('' if strings.language == 'pt' else '_en') + suffix


def loading_view(strings):
    """The loading view of buttonPressed: and tutorialSelected: (visual only): backTelaLoad drawn over the
    screen, the ship animation (01 to 30, one second a loop, W / 6 square, above the middle) and "Loading..."
    in white below it. It fades in over 2 seconds. Positions are approximate, from the decompiled frames."""
    from ..engine import actions as A
    root = Node(name='loading')
    root.alpha, root.z = 0.0, 100
    root.add_child(image('backTelaLoad', 0, 0, W, H))
    frames = ['%02d' % i for i in range(1, 31)]
    ship = image(frames[0], W / 2 - W / 12, H / 2 - W / 6 - 10, W / 6, W / 6, z=1)
    ship.run(A.repeat_forever(A.animate_with_textures(frames, 1.0 / 30)))
    root.add_child(ship)
    root.add_child(text(strings.get('tela_load') + '...', W / 4, H / 2, W / 2, 50, 17, 'HelveticaNeue', z=1))
    root.run(A.fade_alpha_to(1.0, 2.0))
    return root


class Doors:
    """The sub screens' doors (leftDoor and rightDoor, the 4-inch versions): they start shut over the screen
    (the left one 0 to W / 2 * 1.124523, the right one the right half), slide open over 1 second when the
    screen appears and shut again over 1 second before it's popped."""

    def __init__(self, view, strings, z=50):
        from ..engine import actions as A
        self.A = A
        lw = W / 2 * 1.124523
        self.left = image(localized('leftDoor', strings, '_4'), 0, 0, lw, H, z=z + 1)
        self.right = image(localized('rightDoor', strings, '_4'), W / 2, 0, W / 2, H, z=z)
        self.width = lw
        view.add_child(self.left)
        view.add_child(self.right)
        self.shut = True

    def open(self, duration=1.0):
        if self.shut:
            self.shut = False
            self.left.run(self.A.move_by(-self.width, 0, duration), key='doors')
            self.right.run(self.A.move_by(W / 2, 0, duration), key='doors')

    def close(self, duration=1.0):
        if not self.shut:
            self.shut = True
            self.left.run(self.A.move_by(self.width, 0, duration), key='doors')
            self.right.run(self.A.move_by(-W / 2, 0, duration), key='doors')


# Global createImageTextWith: text spelled with letter pictures: AlfabetoAct_ (orange, active) or
# Alfabeto_ (grey). Accented letters are the base letter plus the UTF-8 bytes of a combining mark, which
# the archive's file names carry as cp437 text.
_MARKS = {'\u0303': '\u2560\u00e2', '\u0302': '\u2560\u00e9', '\u0301': '\u2560\u00fc', '\u0327': '\u2560\u00ba'}
GLYPH_H = 146.0


def glyph_name(ch, active):
    import unicodedata
    prefix = 'AlfabetoAct_' if active else 'Alfabeto_'
    if ch == ' ':
        return prefix
    if ch in '-_':
        return prefix + '_'
    d = unicodedata.normalize('NFD', ch.upper())
    return prefix + d[0] + ''.join(_MARKS.get(m, '') for m in d[1:])


def glyph_text(value, scale, box_w, active, textures):
    """A node holding `value` spelled in letter pictures at `scale`, wrapped into lines no wider than box_w,
    each line centred, the block centred on the node."""
    root = Node(name='glyphText')
    h = GLYPH_H * scale
    def width_of(word):
        total = 0.0
        for ch in word:
            tex = textures.get(glyph_name(ch, active))
            total += (tex.get_width() if tex is not None else 60) * scale
        return total
    space = width_of(' ')
    lines, line = [], ''
    for word in value.split():
        trial = (line + ' ' + word).strip()
        if line and width_of(trial) > box_w:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    for i, text_line in enumerate(lines):
        x = -width_of(text_line) / 2
        y = (len(lines) - 1) * h / 2 - i * h
        for ch in text_line:
            name = glyph_name(ch, active)
            tex = textures.get(name)
            w = (tex.get_width() if tex is not None else 60) * scale
            if ch != ' ' and tex is not None:
                g = Node(name='glyph', size=(w, h), position=(x + w / 2, y))
                g.texture = name
                root.add_child(g)
            x += w
    return root
