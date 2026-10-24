"""OpenGL 3.3 composition, with no CPU sprite transforms or alpha blending.

This is the first migration stage, not the feature-complete show renderer.
The owning thread/process must also own the OpenGL context.
"""

import math

import numpy as np


VERTEX = """
#version 330
in vec2 corner;
uniform vec2 canvas, origin, size, pivot;
uniform float angle;
uniform bool flip, flip_y;
out vec2 uv;
void main() {
    vec2 p = (corner-pivot)*size;
    float c=cos(angle), s=sin(angle);
    p = vec2(c*p.x-s*p.y, s*p.x+c*p.y)+origin;
    gl_Position = vec4(2.0*p.x/canvas.x-1.0, 1.0-2.0*p.y/canvas.y, 0, 1);
    uv = vec2(flip ? 1.0-corner.x : corner.x, flip_y ? 1.0-corner.y : corner.y);
}
"""
FRAGMENT = """
#version 330
uniform sampler2D image;
uniform float opacity;
in vec2 uv;
out vec4 color;
void main() {
    vec4 texel = texture(image, uv);
    color = vec4(texel.rgb, texel.a*opacity);
}
"""


def software_renderer(name):
    return any(
        word in name.lower() for word in ("llvmpipe", "softpipe", "swrast", "software")
    )


class GpuCanvas:
    """Camera-space viewport target accepted by head effects and visitor cues."""

    def __init__(self, renderer, width, height, offset):
        self.renderer = renderer
        self.shape = (height, width, 3)
        self.offset = offset

    def sprite(
        self,
        asset,
        x,
        y,
        width,
        height,
        angle=0,
        alpha=1,
        flip=False,
        anchor=(0.5, 0.5),
    ):
        self.renderer.sprite(
            asset,
            x + self.offset[0],
            y + self.offset[1],
            width,
            height,
            angle,
            alpha,
            flip,
            anchor,
        )

    def line(self, start, end, color, width, alpha=1):
        dx, dy = end[0] - start[0], end[1] - start[1]
        # A tiny solid texture becomes a rotated strip on the GPU.
        color = tuple(color)
        if color not in self.renderer.solids:
            self.renderer.solids[color] = np.array([[(*color, 255)]], np.uint8)
        self.sprite(
            self.renderer.solids[color],
            (start[0] + end[0]) / 2,
            (start[1] + end[1]) / 2,
            max(1, math.hypot(dx, dy)),
            width,
            angle=-math.degrees(math.atan2(dy, dx)),
            alpha=alpha,
        )


class GpuRenderer:
    def __init__(self, context, width, height, allow_software=False):
        import moderngl

        self.ctx = context
        self.width, self.height = width, height
        self.info = {
            key: str(context.info[key])
            for key in ("GL_VENDOR", "GL_RENDERER", "GL_VERSION")
        }
        self.hardware = not software_renderer(self.info["GL_RENDERER"])
        if not self.hardware and not allow_software:
            raise RuntimeError(
                "Software OpenGL renderer rejected: " + self.info["GL_RENDERER"]
            )
        self.program = context.program(vertex_shader=VERTEX, fragment_shader=FRAGMENT)
        self.vertices = context.buffer(
            np.array([(0, 0), (1, 0), (0, 1), (1, 1)], "f4").tobytes()
        )
        self.quad = context.vertex_array(
            self.program, [(self.vertices, "2f", "corner")]
        )
        self.output = context.texture((width, height), 3)
        self.fbo = context.framebuffer([self.output])
        self.cache = {}
        self.camera_texture = None
        self.camera_size = None
        self.white = np.full((1, 1, 4), 255, np.uint8)
        self.solids = {}
        self.program["image"] = 0
        self.program["canvas"] = (width, height)
        context.enable(moderngl.BLEND)
        context.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

    def _draw(
        self,
        texture,
        x,
        y,
        width,
        height,
        angle=0,
        alpha=1,
        flip=False,
        anchor=(0.5, 0.5),
        flip_y=False,
    ):
        import moderngl

        texture.use(0)
        for name, value in dict(
            origin=(x, y),
            size=(width, height),
            pivot=anchor,
            angle=math.radians(-angle),
            opacity=alpha,
            flip=flip,
            flip_y=flip_y,
        ).items():
            self.program[name] = value
        self.quad.render(moderngl.TRIANGLE_STRIP)

    def begin(self, bgr):
        """Upload source-size BGR; shaders perform scaling and letterboxing."""
        import moderngl

        h, w = bgr.shape[:2]
        if self.camera_size != (w, h):
            if self.camera_texture:
                self.camera_texture.release()
            self.camera_texture = self.ctx.texture((w, h), 3)
            self.camera_texture.swizzle = "BGR1"
            self.camera_texture.filter = moderngl.LINEAR, moderngl.LINEAR
            self.camera_texture.repeat_x = self.camera_texture.repeat_y = False
            self.camera_size = w, h
        self.camera_texture.write(np.ascontiguousarray(bgr).tobytes(), alignment=1)
        self.fbo.use()
        self.ctx.scissor = None
        self.ctx.viewport = (0, 0, self.width, self.height)
        self.fbo.clear(20 / 255, 10 / 255, 15 / 255)
        scale = min(self.width / w, self.height / h)
        vw, vh = round(w * scale), round(h * scale)
        offset = ((self.width - vw) // 2, (self.height - vh) // 2)
        self._draw(self.camera_texture, *offset, vw, vh, anchor=(0, 0))
        # Effects must not spill into the letterbox bars.
        self.ctx.scissor = (offset[0], self.height - offset[1] - vh, vw, vh)
        return GpuCanvas(self, vw, vh, offset)

    def sprite(
        self,
        asset,
        x,
        y,
        width,
        height,
        angle=0,
        alpha=1,
        flip=False,
        anchor=(0.5, 0.5),
    ):
        import moderngl

        key = id(asset)
        if key not in self.cache:
            if len(self.cache) >= 128:
                raise RuntimeError("Sprite cache capacity exceeded")
            h, w = asset.shape[:2]
            texture = self.ctx.texture(
                (w, h), 4, np.ascontiguousarray(asset).tobytes(), alignment=1
            )
            texture.swizzle = "BGRA"
            texture.repeat_x = texture.repeat_y = False
            texture.filter = moderngl.LINEAR, moderngl.LINEAR
            # Hold the source too: an id must not be reused for a different asset.
            self.cache[key] = (asset, texture)
        self._draw(self.cache[key][1], x, y, width, height, angle, alpha, flip, anchor)

    def present(self, window_size=None):
        """GPU framebuffer-to-window copy, without full-resolution CPU readback."""
        self.ctx.scissor = None
        screen = self.ctx.screen
        screen.use()
        sw, sh = window_size or screen.size
        self.ctx.viewport = (0, 0, sw, sh)
        screen.clear(20 / 255, 10 / 255, 15 / 255)
        scale = min(sw / self.width, sh / self.height)
        w, h = round(self.width * scale), round(self.height * scale)
        self.program["canvas"] = (sw, sh)
        self._draw(
            self.output, (sw - w) // 2, (sh - h) // 2, w, h, anchor=(0, 0), flip_y=True
        )
        self.program["canvas"] = (self.width, self.height)

    def read(self):
        """Explicit diagnostic readback, never used for normal presentation."""
        self.ctx.scissor = None
        data = self.fbo.read(components=3, alignment=1)
        return (
            np.frombuffer(data, np.uint8)
            .reshape(self.height, self.width, 3)[::-1, :, ::-1]
            .copy()
        )

    def close(self):
        self.ctx.scissor = None
        for _, texture in self.cache.values():
            texture.release()
        self.cache.clear()
        if self.camera_texture:
            self.camera_texture.release()
        for resource in (self.fbo, self.output, self.quad, self.vertices, self.program):
            resource.release()
