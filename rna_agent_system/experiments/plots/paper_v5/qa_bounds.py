"""Objective bounds QA: every text/patch artist must sit inside its figure.

Run:  python qa_bounds.py [fig2 fig3 ...]
Reports any artist whose rendered bounding box pokes outside the figure
(tolerance 2 px at draw dpi). Complements the vision-model QA.
"""
import sys, pathlib
import matplotlib
matplotlib.use("Agg")

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import style as S

orig_save = S.save_panel
report = []
TOL = 2.0


def audited_save(fig, out_base, dpi=450):
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    W, H = fig.get_size_inches() * fig.dpi
    bad = []

    def check(artist, label):
        try:
            bb = artist.get_window_extent(r)
        except Exception:
            return
        if bb.x0 < -TOL or bb.y0 < -TOL or bb.x1 > W + TOL or bb.y1 > H + TOL:
            bad.append(f"{label}: bbox=({bb.x0:.0f},{bb.y0:.0f})-({bb.x1:.0f},{bb.y1:.0f}) fig=({W:.0f},{H:.0f})")

    for ax in fig.axes:
        for t in ax.texts:
            if t.get_text().strip():
                check(t, "text " + t.get_text().replace("\n", " ")[:32])
        for p in ax.patches:
            check(p, type(p).__name__)
        # data lines / collections are clipped by the axes by design - skip them
        if ax.get_title():
            check(ax.title, "title " + ax.get_title()[:28])
        for lab in (ax.xaxis.label, ax.yaxis.label):
            if lab.get_text().strip():
                check(lab, "label " + lab.get_text()[:24])
        if not getattr(ax, "axison", True):
            continue
        for axis, lims in ((ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())):
            for t in axis.get_ticklabels():
                if not (t.get_text() and t.get_visible()):
                    continue
                loc = t.get_position()[0] if axis is ax.xaxis else t.get_position()[1]
                if not (min(lims) - 1e-9 <= loc <= max(lims) + 1e-9):
                    continue  # tick outside the view interval is never drawn
                check(t, "tick " + t.get_text()[:16])
    if bad:
        report.append((out_base, bad))
    orig_save(fig, out_base, dpi)


S.save_panel = audited_save


def main(figdirs):
    for d in figdirs:
        for script in sorted((HERE / d).glob("*.py")):
            if script.name == "assemble.py":
                continue
            g = {"__file__": str(script), "__name__": "__main__"}
            try:
                exec(compile(script.read_text(), str(script), "exec"), g)
            except Exception as e:  # noqa: BLE001
                report.append((str(script), [f"EXEC ERROR: {e}"]))
    if report:
        for base, bad in report:
            print(f"[OOB] {base}")
            for b in bad:
                print("   ", b)
        sys.exit(1)
    print("bounds QA: all panels within figure bounds")


if __name__ == "__main__":
    args = sys.argv[1:] or [f"fig{i}" for i in range(1, 7)]
    main([a for a in args if (HERE / a).is_dir()])
