from baebugs.hypergraph import build, walk_to_truth, lomo_actors


def test_connected_and_lomo():
    g = build(".")
    assert g["counts"]["toy"] == 91 and g["counts"]["datasets_root"] == 1
    assert walk_to_truth(g, "dataset:multires_mp_1")[-1][2].startswith("truth:")
    r = lomo_actors(".", "exact")
    assert r["baseline"] and all(v["flips"] >= 0 for v in r["leave_one_actor_out"].values())
