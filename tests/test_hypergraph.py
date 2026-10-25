from baebugs.hypergraph import build, walk_to_truth, lomo_actors


def test_connected_and_lomo():
    g = build(".")
    assert g["counts"]["toy"] == 91 and g["counts"]["datasets_root"] == 1
    assert walk_to_truth(g, "dataset:multires_mp_1")[-1][2].startswith("truth:")
    r = lomo_actors(".", "exact")
    assert r["baseline"] and all(v["flips"] >= 0 for v in r["leave_one_actor_out"].values())


def test_lomo_three_modes():
    from baebugs.hypergraph import lomo_graph
    r = lomo_graph(".")
    assert r["module"]["insect_lomo"]["consensus_after"]["exact"]          # removing the reference -> unverified
    assert all(k.startswith(("dataset:", "kgroot:", "protocol:", "truth:")) for k in r["merkle"])
    assert any(k.startswith("hybrid:") for k in r["custody_break"])
