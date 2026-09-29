"""Measured palette-pair design targets; not an accessibility conformance claim."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from story_atlas.theme import PALETTES


def luminance(color):
    channels = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
    return sum(weight * (c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4)
               for weight, c in zip((.2126, .7152, .0722), channels))


def contrast(a, b):
    light, dark = sorted((luminance(a), luminance(b)), reverse=True)
    return (light + .05) / (dark + .05)


def audit():
    # These are actual enabled-state palette pairings. Disabled controls and
    # artwork are excluded; selected Treeviews use text, never muted text.
    pairs = [('text', surface, 4.5) for surface in ('bg','panel','detail','input','hover','selected','navigation')]
    pairs += [('muted', surface, 4.5) for surface in ('bg','panel','detail')]
    pairs += [('on_accent', surface, 4.5) for surface in ('accent','primary_hover','primary_pressed')]
    pairs += [('context_text','context',4.5), ('error','bg',4.5), ('error','panel',4.5)]
    pairs += [('error','hover',4.5), ('error','selected',4.5), ('success','bg',4.5)]
    pairs += [(key, surface, 3) for key in ('border','focus')
              for surface in ('bg','panel','detail','input','hover','selected','navigation')]
    return [dict(theme=theme, foreground=fg, background=bg, foreground_hex=p[fg],
                 background_hex=p[bg], ratio=contrast(p[fg],p[bg]), target=target,
                 passed=contrast(p[fg],p[bg]) >= target)
            for theme,p in PALETTES.items() for fg,bg,target in pairs]


if __name__ == '__main__':
    results = audit()
    print(json.dumps(results, indent=2))
    raise SystemExit(0 if all(row['passed'] for row in results) else 1)
