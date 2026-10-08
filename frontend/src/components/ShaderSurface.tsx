"use client";
import { useEffect, useState, useRef } from "react";
import { MeshGradient, DotGrid } from "@paper-design/shaders-react";
const colors = ["#faf8f6", "#f0eeeb", "#f5e9e6", "#faf9f7"];
export default function ShaderSurface() {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(true);
  const [ready, setReady] = useState(false),
    [motion, setMotion] = useState(false);
  useEffect(() => {
    const canvas = document.createElement("canvas");
    const gl = canvas.getContext("webgl2");
    if (gl) {
      gl.getExtension("WEBGL_lose_context")?.loseContext();
      setReady(true);
    }
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    setMotion(!media.matches);
    const change = () => setMotion(!media.matches);
    media.addEventListener("change", change);
    useEffect(() => {
      let inView = true;
      const update = () => setVisible(inView && !document.hidden);
      const observer = new IntersectionObserver((entries) => {
        inView = entries[0].isIntersecting;
        update();
      });
      if (ref.current) observer.observe(ref.current);
      document.addEventListener("visibilitychange", update);
      return () => {
        observer.disconnect();
        document.removeEventListener("visibilitychange", update);
      };
    }, []);
    return () => media.removeEventListener("change", change);
  }, []);
  useEffect(() => {
    let inView = true;
    const update = () => setVisible(inView && !document.hidden);
    const observer = new IntersectionObserver((entries) => {
      inView = entries[0].isIntersecting;
      update();
    });
    if (ref.current) observer.observe(ref.current);
    document.addEventListener("visibilitychange", update);
    return () => {
      observer.disconnect();
      document.removeEventListener("visibilitychange", update);
    };
  }, []);
  return (
    <div ref={ref} className="shader-surface" aria-hidden="true">
      <div className="shader-mesh">
        {ready && (
          <MeshGradient
            colors={colors}
            speed={motion && visible ? 0.08 : 0}
            distortion={0.3}
            swirl={0.2}
            grainMixer={0.05}
            grainOverlay={0.12}
            maxPixelCount={1200000}
            style={{ width: "100%", height: "100%" }}
          />
        )}
      </div>
      <div className="shader-dots">
        {ready && (
          <DotGrid
            colorBack="#00000000"
            colorFill="#2a272420"
            colorStroke="#2a272400"
            size={1}
            gapX={20}
            gapY={20}
            opacityRange={0.25}
            shape="square"
            maxPixelCount={200000}
            style={{ width: "100%", height: "100%" }}
          />
        )}
      </div>
    </div>
  );
}
