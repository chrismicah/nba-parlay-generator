import React from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface GlowCardProps {
  children: React.ReactNode;
  className?: string;
  glowColor?: string;
  onClick?: () => void;
}

export const GlowCard: React.FC<GlowCardProps> = ({
  children,
  className,
  glowColor = "blue",
  onClick
}) => {
  const [mousePosition, setMousePosition] = React.useState({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = React.useState(false);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setMousePosition({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
  };

  const glowColors = {
    blue: "rgba(59, 130, 246, 0.5)",
    purple: "rgba(147, 51, 234, 0.5)",
    orange: "rgba(249, 115, 22, 0.5)",
    green: "rgba(34, 197, 94, 0.5)",
    pink: "rgba(236, 72, 153, 0.5)",
  };

  return (
    <motion.div
      className={cn(
        "relative group cursor-pointer",
        className
      )}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={onClick}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
    >
      {/* Glow effect */}
      <div
        className="absolute -inset-0.5 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-sm"
        style={{
          background: `radial-gradient(600px circle at ${mousePosition.x}px ${mousePosition.y}px, ${glowColors[glowColor as keyof typeof glowColors]}, transparent 40%)`,
        }}
      />
      
      {/* Main card */}
      <div className="relative bg-white/90 backdrop-blur-sm border border-white/20 rounded-xl p-6 shadow-xl transition-all duration-300 group-hover:shadow-2xl">
        {/* Animated border */}
        <div 
          className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"
          style={{
            background: `linear-gradient(90deg, transparent, ${glowColors[glowColor as keyof typeof glowColors]}, transparent)`,
            backgroundSize: "200% 100%",
            animation: isHovered ? "borderMove 3s linear infinite" : "none",
          }}
        />
        
        <div className="relative z-10">
          {children}
        </div>
      </div>

      <style jsx>{`
        @keyframes borderMove {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
      `}</style>
    </motion.div>
  );
};



