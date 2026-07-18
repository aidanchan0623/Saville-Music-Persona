import { useEffect, useRef } from "react";
import "./LineWaves.css";

interface LineWavesProps {
  speed?: number;
  innerLineCount?: number;
  outerLineCount?: number;
  warpIntensity?: number;
  rotation?: number;
  edgeFadeWidth?: number;
  colorCycleSpeed?: number;
  brightness?: number;
  color1?: string;
  color2?: string;
  color3?: string;
  enableMouseInteraction?: boolean;
  mouseInfluence?: number;
  className?: string;
}

type Vec3 = [number, number, number];
type OglModule = typeof import("ogl");
type OglProgram = InstanceType<OglModule["Program"]>;

interface LineWavesUniforms {
  uTime: { value: number };
  uResolution: { value: [number, number, number] };
  uSpeed: { value: number };
  uInnerLines: { value: number };
  uOuterLines: { value: number };
  uWarpIntensity: { value: number };
  uRotation: { value: number };
  uEdgeFadeWidth: { value: number };
  uColorCycleSpeed: { value: number };
  uBrightness: { value: number };
  uColor1: { value: Vec3 };
  uColor2: { value: Vec3 };
  uColor3: { value: Vec3 };
  uMouse: { value: Float32Array };
  uMouseInfluence: { value: number };
  uEnableMouse: { value: boolean };
}

function hexToVec3(hex: string): Vec3 {
  const fallback: Vec3 = [1, 1, 1];
  const h = hex.replace("#", "").trim();
  if (!/^[0-9a-fA-F]{6}$/.test(h)) return fallback;
  return [
    parseInt(h.slice(0, 2), 16) / 255,
    parseInt(h.slice(2, 4), 16) / 255,
    parseInt(h.slice(4, 6), 16) / 255,
  ];
}

function prefersReducedMotion() {
  return typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function supportsWebGL() {
  if (typeof document === "undefined") return false;
  const canvas = document.createElement("canvas");
  return Boolean(canvas.getContext("webgl2") || canvas.getContext("webgl"));
}

const vertexShader = `
attribute vec2 uv;
attribute vec2 position;
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = vec4(position, 0, 1);
}
`;

const fragmentShader = `
precision highp float;

uniform float uTime;
uniform vec3 uResolution;
uniform float uSpeed;
uniform float uInnerLines;
uniform float uOuterLines;
uniform float uWarpIntensity;
uniform float uRotation;
uniform float uEdgeFadeWidth;
uniform float uColorCycleSpeed;
uniform float uBrightness;
uniform vec3 uColor1;
uniform vec3 uColor2;
uniform vec3 uColor3;
uniform vec2 uMouse;
uniform float uMouseInfluence;
uniform bool uEnableMouse;

#define HALF_PI 1.5707963

float hashF(float n) {
  return fract(sin(n * 127.1) * 43758.5453123);
}

float smoothNoise(float x) {
  float i = floor(x);
  float f = fract(x);
  float u = f * f * (3.0 - 2.0 * f);
  return mix(hashF(i), hashF(i + 1.0), u);
}

float displaceA(float coord, float t) {
  float result = sin(coord * 2.123) * 0.2;
  result += sin(coord * 3.234 + t * 4.345) * 0.1;
  result += sin(coord * 0.589 + t * 0.934) * 0.5;
  return result;
}

float displaceB(float coord, float t) {
  float result = sin(coord * 1.345) * 0.3;
  result += sin(coord * 2.734 + t * 3.345) * 0.2;
  result += sin(coord * 0.189 + t * 0.934) * 0.3;
  return result;
}

vec2 rotate2D(vec2 p, float angle) {
  float c = cos(angle);
  float s = sin(angle);
  return vec2(p.x * c - p.y * s, p.x * s + p.y * c);
}

void main() {
  vec2 coords = gl_FragCoord.xy / uResolution.xy;
  coords = coords * 2.0 - 1.0;
  coords = rotate2D(coords, uRotation);

  float halfT = uTime * uSpeed * 0.5;
  float fullT = uTime * uSpeed;

  float mouseWarp = 0.0;
  if (uEnableMouse) {
    vec2 mPos = rotate2D(uMouse * 2.0 - 1.0, uRotation);
    float mDist = length(coords - mPos);
    mouseWarp = uMouseInfluence * exp(-mDist * mDist * 4.0);
  }

  float warpAx = coords.x + displaceA(coords.y, halfT) * uWarpIntensity + mouseWarp;
  float warpAy = coords.y - displaceA(coords.x * cos(fullT) * 1.235, halfT) * uWarpIntensity;
  float warpBx = coords.x + displaceB(coords.y, halfT) * uWarpIntensity + mouseWarp;
  float warpBy = coords.y - displaceB(coords.x * sin(fullT) * 1.235, halfT) * uWarpIntensity;

  vec2 fieldA = vec2(warpAx, warpAy);
  vec2 fieldB = vec2(warpBx, warpBy);
  vec2 blended = mix(fieldA, fieldB, mix(fieldA, fieldB, 0.5));

  float fadeTop = smoothstep(uEdgeFadeWidth, uEdgeFadeWidth + 0.4, blended.y);
  float fadeBottom = smoothstep(-uEdgeFadeWidth, -(uEdgeFadeWidth + 0.4), blended.y);
  float vMask = 1.0 - max(fadeTop, fadeBottom);

  float tileCount = mix(uOuterLines, uInnerLines, vMask);
  float scaledY = blended.y * tileCount;
  float nY = smoothNoise(abs(scaledY));

  float ridge = pow(
    step(abs(nY - blended.x) * 2.0, HALF_PI) * cos(2.0 * (nY - blended.x)),
    5.0
  );

  float lines = 0.0;
  for (float i = 1.0; i < 3.0; i += 1.0) {
    lines += pow(max(fract(scaledY), fract(-scaledY)), i * 2.0);
  }

  float pattern = vMask * lines;

  float cycleT = fullT * uColorCycleSpeed;
  float rChannel = (pattern + lines * ridge) * (cos(blended.y + cycleT * 0.234) * 0.5 + 1.0);
  float gChannel = (pattern + vMask * ridge) * (sin(blended.x + cycleT * 1.745) * 0.5 + 1.0);
  float bChannel = (pattern + lines * ridge) * (cos(blended.x + cycleT * 0.534) * 0.5 + 1.0);

  vec3 col = (rChannel * uColor1 + gChannel * uColor2 + bChannel * uColor3) * uBrightness;
  float alpha = clamp(length(col), 0.0, 1.0);

  gl_FragColor = vec4(col, alpha);
}
`;

export default function LineWaves({
  speed = 0.3,
  innerLineCount = 32,
  outerLineCount = 36,
  warpIntensity = 1,
  rotation = -45,
  edgeFadeWidth = 0,
  colorCycleSpeed = 1,
  brightness = 0.2,
  color1 = "#ffffff",
  color2 = "#ffffff",
  color3 = "#ffffff",
  enableMouseInteraction = true,
  mouseInfluence = 2,
  className = "",
}: LineWavesProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || prefersReducedMotion() || !supportsWebGL()) return;

    let mounted = true;
    let animationFrameId: number | null = null;
    let resizeFrameId: number | null = null;
    let removeListeners = () => {};

    void import("ogl").then(({ Renderer, Program, Mesh, Triangle }) => {
      if (!mounted || !container.isConnected) return;

      const renderer = new Renderer({ alpha: true, premultipliedAlpha: false });
      const gl = renderer.gl;
      const canvas = gl.canvas;
      canvas.className = "line-waves__canvas";
      canvas.setAttribute("aria-hidden", "true");
      gl.clearColor(0, 0, 0, 0);

      let currentMouse: [number, number] = [0.5, 0.5];
      let targetMouse: [number, number] = [0.5, 0.5];

      const resize = () => {
        const width = Math.max(1, container.clientWidth);
        const height = Math.max(1, container.clientHeight);
        renderer.setSize(width, height);
        program.uniforms.uResolution.value = [canvas.width, canvas.height, canvas.width / canvas.height];
      };

      const scheduleResize = () => {
        if (resizeFrameId !== null) cancelAnimationFrame(resizeFrameId);
        resizeFrameId = requestAnimationFrame(() => {
          resizeFrameId = null;
          resize();
        });
      };

      const handlePointerMove = (event: PointerEvent) => {
        const rect = container.getBoundingClientRect();
        if (!rect.width || !rect.height) return;
        targetMouse = [
          (event.clientX - rect.left) / rect.width,
          1 - (event.clientY - rect.top) / rect.height,
        ];
      };

      const handlePointerOut = (event: PointerEvent) => {
        if (event.relatedTarget === null) targetMouse = [0.5, 0.5];
      };

      const geometry = new Triangle(gl);
      const program = new Program(gl, {
        vertex: vertexShader,
        fragment: fragmentShader,
        uniforms: {
          uTime: { value: 0 },
          uResolution: { value: [1, 1, 1] },
          uSpeed: { value: speed },
          uInnerLines: { value: innerLineCount },
          uOuterLines: { value: outerLineCount },
          uWarpIntensity: { value: warpIntensity },
          uRotation: { value: (rotation * Math.PI) / 180 },
          uEdgeFadeWidth: { value: edgeFadeWidth },
          uColorCycleSpeed: { value: colorCycleSpeed },
          uBrightness: { value: brightness },
          uColor1: { value: hexToVec3(color1) },
          uColor2: { value: hexToVec3(color2) },
          uColor3: { value: hexToVec3(color3) },
          uMouse: { value: new Float32Array([0.5, 0.5]) },
          uMouseInfluence: { value: mouseInfluence },
          uEnableMouse: { value: enableMouseInteraction },
        },
      }) as OglProgram & { uniforms: LineWavesUniforms };
      const mesh = new Mesh(gl, { geometry, program });

      container.appendChild(canvas);
      resize();
      scheduleResize();
      const resizeObserver = typeof ResizeObserver !== "undefined" ? new ResizeObserver(scheduleResize) : null;
      resizeObserver?.observe(container);
      window.addEventListener("resize", resize);
      if (enableMouseInteraction) {
        window.addEventListener("pointermove", handlePointerMove, { passive: true });
        window.addEventListener("pointerout", handlePointerOut);
      }

      const update = (time: number) => {
        if (!mounted) return;
        animationFrameId = requestAnimationFrame(update);
        program.uniforms.uTime.value = time * 0.001;

        if (enableMouseInteraction) {
          currentMouse[0] += 0.05 * (targetMouse[0] - currentMouse[0]);
          currentMouse[1] += 0.05 * (targetMouse[1] - currentMouse[1]);
          program.uniforms.uMouse.value[0] = currentMouse[0];
          program.uniforms.uMouse.value[1] = currentMouse[1];
        } else {
          program.uniforms.uMouse.value[0] = 0.5;
          program.uniforms.uMouse.value[1] = 0.5;
        }

        renderer.render({ scene: mesh });
      };

      animationFrameId = requestAnimationFrame(update);

      removeListeners = () => {
        window.removeEventListener("resize", resize);
        resizeObserver?.disconnect();
        if (resizeFrameId !== null) cancelAnimationFrame(resizeFrameId);
        if (enableMouseInteraction) {
          window.removeEventListener("pointermove", handlePointerMove);
          window.removeEventListener("pointerout", handlePointerOut);
        }
        if (animationFrameId !== null) cancelAnimationFrame(animationFrameId);
        if (canvas.parentNode === container) container.removeChild(canvas);
        gl.getExtension("WEBGL_lose_context")?.loseContext();
      };
    });

    return () => {
      mounted = false;
      removeListeners();
    };
  }, [speed, innerLineCount, outerLineCount, warpIntensity, rotation, edgeFadeWidth, colorCycleSpeed, brightness, color1, color2, color3, enableMouseInteraction, mouseInfluence]);

  return <div ref={containerRef} className={`line-waves line-waves--fallback${className ? ` ${className}` : ""}`} aria-hidden="true" />;
}
