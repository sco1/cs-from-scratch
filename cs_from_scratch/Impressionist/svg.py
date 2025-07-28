from pathlib import Path

from cs_from_scratch.Impressionist import COLOR_T, COORDS_T, Coord


class SVG:
    def __init__(self, width: int, height: int, bg_color: COLOR_T) -> None:
        self.content = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            f'<svg version="1.1" baseProfile="full" width="{width}" '
            f'height="{height}" xmlns="http://www.w3.org/2000/svg">\n'
            f'<rect width="100%" height="100%" fill="rgb{bg_color}" />'
        )

    def draw_ellipse(self, p1: Coord, p2: Coord, color: COLOR_T) -> None:
        self.content += (
            f'<ellipse cx="{(p1.x + p2.x) // 2}" cy="{(p1.y + p2.y) // 2}" '
            f'rx="{abs(p1.x - p2.x) // 2}" ry="{abs(p1.y - p2.y) // 2}" '
            f'fill="rgb{color}" />\n'
        )

    def draw_line(self, p1: Coord, p2: Coord, color: COLOR_T) -> None:
        self.content += (
            f'<line x1="{p1.x}" y1="{p1.y}" x2="{p2.x}" y2="{p2.y}" stroke="rgb{color}" '
            'stroke-width="1px" shape-rendering="crispEdges" />\n'
        )

    def draw_polygon(self, points: COORDS_T, color: COLOR_T) -> None:
        point_strings = (f"{p.x},{p.y} " for p in points)
        self.content += f'<polygon points="{''.join(point_strings)}" fill="rgb{color}" />\n'

    def write(self, out_filepath: Path) -> None:
        self.content += "</svg>\n"
        out_filepath.write_text(self.content)
