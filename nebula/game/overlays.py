"""The pictures of the in-game menus and free mode's score, traced from the original. Visual only.

- Pause (callPause): a black node at 80% over the screen (z 8) holding the "pause" picture, W / 1.2 by
  H / 1.775, in the middle. The buttons are drawn in the picture; their nodes are invisible.
- Game over, mission complete, tutorial complete: an invisible node holding the "gameOver", "missaoCompleta"
  or "tutorialCompleto" picture (same size, z 80, mission complete z 90). Both start transparent and fade in
  over 0.5 seconds.
- Free mode game over also shows scoreFinal (W * 0.8 by H / 7.1, z 90) near the top, with the score under
  SCORE and the best score under BEST SCORE, in yellow.
- Free mode's play screen: base_score at the top with the score in yellow on it (z 8), and the countdown in
  large white thin type in the middle (z 5).

Picture names follow Global checkImageTelaJPG: the "_en" version in any language but Portuguese.
"""
from ..engine import actions as A
from ..engine.nodes import Node

YELLOW, WHITE = (1.0, 1.0, 0.0), (1.0, 1.0, 1.0)
FADE = 0.5


def localized(name, strings):
    return name if strings.language == 'pt' else name + '_en'


def label(text, position, size, color, font, z):
    n = Node(name='label', position=position)
    n.text, n.font_size, n.font_color, n.font_name, n.z = text, size, color, font, z
    return n


def _picture(scene, name, z):
    W, H = scene.size
    pic = Node(name='menuPicture', size=(W / 1.2, H / 1.775))
    pic.texture, pic.z = localized(name, scene.services.strings), z
    return pic


def pause(scene):
    W, H = scene.size
    bg = Node(name='Pause background', size=(W, H), position=(W / 2, H / 2))
    bg.color, bg.z = (0.0, 0.0, 0.0, 0.8), 8
    bg.add_child(_picture(scene, 'pause', 8))
    scene.add_child(bg)
    return bg


def end_screen(scene, name, z=80):
    W, H = scene.size
    bg = Node(name='endScreen', size=(W, H), position=(W / 2, H / 2))
    bg.alpha = 0.0
    pic = _picture(scene, name, z)
    pic.alpha = 0.0
    bg.add_child(pic)
    scene.add_child(bg)
    bg.run(A.fade_alpha_to(1.0, FADE))
    pic.run(A.fade_alpha_to(1.0, FADE))
    return bg


def final_score(scene, score, best):
    W, H = scene.size
    panel = Node(name='scoreFinal', size=(W * 0.8, H / 7.1), position=(W / 2, H * 0.9296))
    panel.texture, panel.z = 'scoreFinal', 90
    size = W / 15
    nodes = [panel, label('%d' % score, (W * 0.3, H * 0.9014), size, YELLOW, 'Futura-CondensedExtraBold', 91),
             label('%d' % best, (W * 0.6915, H * 0.9014), size, YELLOW, 'Futura-CondensedExtraBold', 91)]
    for n in nodes:
        scene.add_child(n)
    return nodes


class FreeModeDisplay:
    """FreeModeScene initWithSize: the score at the top and the countdown label."""

    def __init__(self, scene):
        W, H = scene.size
        base = Node(name='base_score', size=(W / 1.7, H / 8.875), position=(W / 2, H * 0.99))
        base.texture, base.z = 'base_score', 8
        self.score = label('0', (W / 2, H * 0.95), W / 15, YELLOW, 'Futura-CondensedExtraBold', 8)
        self.count = label('', (W / 2, H / 2), W * 0.125, WHITE, 'HelveticaNeue-Thin', 5)
        for n in (base, self.score, self.count):
            scene.add_child(n)

    def set_score(self, value):
        self.score.text = '%d' % value

    def set_count(self, text):
        self.count.text = text

    def remove_count(self):
        self.count.remove_from_parent()
