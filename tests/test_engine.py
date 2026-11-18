import pytest

from nebula.engine import actions as A
from nebula.engine.nodes import Node, Scene
from nebula.engine.scheduler import Scheduler

FRAME = 1 / 60


def run_frames(scene, seconds, dt=FRAME):
    for _ in range(int(round(seconds / dt))):
        scene.step(dt)


def scene_with(node):
    s = Scene()
    s.add_child(node)
    return s


def test_move_to_reaches_target_linearly():
    n = Node(position=(0, 0))
    s = scene_with(n)
    n.run(A.move_to(100, 50, 2.0))
    run_frames(s, 1.0)
    assert n.position == pytest.approx((50, 25), abs=1e-6)
    run_frames(s, 1.5)
    assert n.position == pytest.approx((100, 50))


def test_leftover_time_carries_into_the_next_action():
    events = []
    n = Node()
    s = scene_with(n)
    n.run(A.sequence([A.wait(0.25), A.run_block(lambda: events.append(s.time))]))
    s.step(0.2)
    assert events == []
    s.step(0.2)
    assert events == [pytest.approx(0.4)]


def test_laser_cycle_timing_matches_the_original_sequence():
    # Ship laser: charge sound, wait 1, firing sound, wait 1.5, beam on.
    marks = []
    n = Node()
    s = scene_with(n)
    n.run(A.sequence([A.run_block(lambda: marks.append(('charge', s.time))), A.wait(1.0),
                      A.run_block(lambda: marks.append(('fire', s.time))), A.wait(1.5),
                      A.run_block(lambda: marks.append(('beam', s.time)))]))
    run_frames(s, 3.0)
    names = [m[0] for m in marks]
    times = [m[1] for m in marks]
    assert names == ['charge', 'fire', 'beam']
    assert times[1] - times[0] == pytest.approx(1.0, abs=FRAME)
    assert times[2] - times[1] == pytest.approx(1.5, abs=FRAME)


def test_concurrent_relative_moves_add_up():
    n = Node(position=(0, 0))
    s = scene_with(n)
    n.run(A.move_by(10, 0, 1.0))
    n.run(A.move_by(0, 20, 1.0))
    run_frames(s, 1.0)
    assert n.position == pytest.approx((10, 20))


def test_tween_reads_start_position_when_it_begins():
    n = Node(position=(0, 0))
    s = scene_with(n)
    n.run(A.sequence([A.move_to(100, 0, 1.0), A.move_to(100, 100, 1.0)]))
    run_frames(s, 1.5)
    assert n.position == pytest.approx((100, 50))


def test_timing_curves_hit_their_endpoints_and_ease_in_out_midpoint():
    for mode in (A.LINEAR, A.EASE_IN, A.EASE_OUT, A.EASE_IN_EASE_OUT):
        assert A.ease(mode, 0.0) == pytest.approx(0.0)
        assert A.ease(mode, 1.0) == pytest.approx(1.0)
    assert A.ease(A.EASE_IN_EASE_OUT, 0.5) == pytest.approx(0.5)
    assert A.ease(A.EASE_IN, 0.5) < 0.5 < A.ease(A.EASE_OUT, 0.5)


def test_repeat_forever_block_then_wait_fires_once_per_interval():
    count = []
    n = Node()
    s = scene_with(n)
    n.run(A.repeat_forever(A.sequence([A.run_block(lambda: count.append(1)), A.wait(1.0)])))
    run_frames(s, 3.5)
    assert len(count) == 4


def test_repeat_forever_of_an_instant_runs_once_per_frame():
    count = []
    n = Node()
    s = scene_with(n)
    n.run(A.repeat_forever(A.run_block(lambda: count.append(1))))
    run_frames(s, 10 * FRAME)
    assert len(count) == 10


def test_repeat_count():
    count = []
    n = Node()
    s = scene_with(n)
    n.run(A.repeat(A.sequence([A.wait(0.5), A.run_block(lambda: count.append(1))]), 3))
    run_frames(s, 5.0)
    assert len(count) == 3


def test_group_ends_with_its_longest_member_and_completion_runs():
    done = []
    n = Node(position=(0, 0))
    s = scene_with(n)
    n.run(A.group([A.move_to_x(10, 0.5), A.move_to_y(10, 2.0)]), completion=lambda: done.append(s.time))
    run_frames(s, 3.0)
    assert done == [pytest.approx(2.0, abs=FRAME)]


def test_keyed_action_replaces_and_can_be_removed():
    hits = []
    n = Node()
    s = scene_with(n)
    n.run(A.repeat_forever(A.sequence([A.wait(1.0), A.run_block(lambda: hits.append('a'))])), key='ShootingAction')
    n.run(A.repeat_forever(A.sequence([A.wait(1.0), A.run_block(lambda: hits.append('b'))])), key='ShootingAction')
    run_frames(s, 2.0)
    assert set(hits) == {'b'}
    n.remove_action('ShootingAction')
    hits.clear()
    run_frames(s, 2.0)
    assert hits == []


def test_remove_from_parent_action_detaches_the_node():
    n = Node()
    s = scene_with(n)
    n.run(A.sequence([A.move_to_y(-20, 1.5), A.remove_from_parent()]))
    run_frames(s, 1.4)
    assert n.parent is s
    run_frames(s, 0.2)
    assert n.parent is None and n.position[1] == pytest.approx(-20)


def test_paused_scene_freezes_actions_but_not_the_scheduler():
    n = Node(position=(0, 0))
    s = scene_with(n)
    clock = Scheduler()
    fired = []
    n.run(A.move_to_x(100, 1.0))
    clock.after(0.5, lambda: fired.append(clock.now))
    s.paused = True
    for _ in range(60):
        clock.update(FRAME)
        s.step(FRAME)
    assert n.position == (0, 0)
    assert fired == [pytest.approx(0.5)]


def test_paused_node_freezes_its_children():
    parent = Node()
    child = Node(position=(0, 0))
    parent.add_child(child)
    s = scene_with(parent)
    child.run(A.move_to_x(100, 1.0))
    parent.paused = True
    run_frames(s, 1.0)
    assert child.position == (0, 0)


def test_scheduler_orders_calls_and_supports_scheduling_from_callbacks():
    clock = Scheduler()
    log = []
    clock.after(1.0, lambda: (log.append(('a', clock.now)), clock.after(0.5, lambda: log.append(('c', clock.now)))))
    clock.after(1.2, lambda: log.append(('b', clock.now)))
    clock.update(2.0)
    assert [x[0] for x in log] == ['a', 'b', 'c']
    assert [x[1] for x in log] == pytest.approx([1.0, 1.2, 1.5])


def test_repeating_timer_fires_on_interval_until_invalidated():
    clock = Scheduler()
    ticks = []

    def tick(timer):
        ticks.append(clock.now)
        if len(ticks) == 3:
            timer.invalidate()
    clock.every(0.1, tick)
    for _ in range(60):
        clock.update(FRAME)
    assert ticks == pytest.approx([0.1, 0.2, 0.3])


def test_wait_with_range_stays_in_bounds_and_does_not_mutate_the_template():
    w = A.wait(4.0, 2.0)
    for _ in range(50):
        n = Node()
        s = scene_with(n)
        done = []
        n.run(w, completion=lambda: done.append(s.time))
        run_frames(s, 5.1)
        assert 3.0 - FRAME <= done[0] <= 5.0 + FRAME
    assert w.duration == 4.0
