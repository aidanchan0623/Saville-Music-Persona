import { useEffect, useRef } from "react";

interface LineWavesProps {
  className?: string;
  lineColor?: string;
  backgroundColor?: string;
  waveCount?: number;
  amplitude?: number;
  speed?: number;
  opacity?: number;
}

export function LineWaves({
  className = "",
  lineColor = "rgba(239,68,68,0.32)",
  backgroundColor = "transparent",
  waveCount = 7,
  amplitude = 34,
  speed = 0.00018,
  opacity = 1,
}: LineWavesProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;

    let frame = 0;
    let width = 0;
    let height = 0;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = Math.max(1, rect.width);
      height = Math.max(1, rect.height);
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
      draw(0);
    };

    const draw = (time: number) => {
      context.clearRect(0, 0, width, height);
      if (backgroundColor !== "transparent") {
        context.fillStyle = backgroundColor;
        context.fillRect(0, 0, width, height);
      }

      const centre = height * 0.5;
      const spacing = Math.max(14, height / Math.max(1, waveCount + 2));
      context.lineCap = "round";

      for (let line = 0; line < waveCount; line += 1) {
        const offset = (line - (waveCount - 1) / 2) * spacing;
        const phase = time * speed + line * 0.55;
        const alpha = 0.12 + (line / Math.max(1, waveCount - 1)) * 0.18;

        context.beginPath();
        context.strokeStyle = lineColor.replace(/[\d.]+\)$/u, `${alpha})`);
        context.lineWidth = line === Math.floor(waveCount / 2) ? 1.4 : 0.9;

        for (let x = -12; x <= width + 12; x += 12) {
          const progress = x / Math.max(1, width);
          const wave =
            Math.sin(progress * Math.PI * 2.1 + phase) * amplitude +
            Math.sin(progress * Math.PI * 4.4 - phase * 1.35) * (amplitude * 0.22);
          const y = centre + offset + wave;
          if (x <= -12) context.moveTo(x, y);
          else context.lineTo(x, y);
        }
        context.stroke();
      }
    };

    const tick = (time: number) => {
      draw(time);
      frame = window.requestAnimationFrame(tick);
    };

    resize();
    window.addEventListener("resize", resize);
    if (!reduceMotion.matches) frame = window.requestAnimationFrame(tick);

    return () => {
      window.removeEventListener("resize", resize);
      window.cancelAnimationFrame(frame);
    };
  }, [amplitude, backgroundColor, lineColor, opacity, speed, waveCount]);

  return <canvas ref={canvasRef} className={`pointer-events-none absolute inset-0 h-full w-full ${className}`} style={{ opacity }} aria-hidden="true" />;
}
