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
