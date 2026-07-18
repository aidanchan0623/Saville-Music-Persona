import type { ChartPoint } from "../types/api";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { GlowPanel } from "./GlowPanel";

const colors = ["#ff4a4d", "#ef2b2d", "#c21f25", "#7b1118", "#a4a4ad", "#f87171", "#fecaca", "#451a1a"];
const axisColor = "#a4a4ad";
const gridColor = "rgba(255,255,255,0.07)";
const tooltipStyle = {
  background: "#111114",
  border: "1px solid rgba(255,255,255,0.14)",
  borderRadius: "8px",
  color: "#f5f5f5",
};
const tooltipLabelStyle = { color: "#ffffff", fontWeight: 700 };

interface Props {
  title: string;
  data: ChartPoint[];
  type?: "bar" | "pie" | "line";
}

export function ChartPanel({ title, data, type = "bar" }: Props) {
  return (
    <GlowPanel as="section" variant="card" className="min-w-0 p-4 md:p-5">
      <h3 className="text-base font-semibold leading-6 text-white md:text-lg">{title}</h3>
      <div className="mt-4 h-64 min-w-0 sm:h-72">
        {data.length === 0 ? (
          <GlowPanel as="div" variant="row" className="grid h-full place-items-center px-4 text-center text-sm leading-6 text-mist">Not enough reliable data for this chart yet.</GlowPanel>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            {type === "pie" ? (
              <PieChart margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
                <Pie data={data} dataKey="value" nameKey="name" innerRadius={54} outerRadius={96} paddingAngle={3}>
                  {data.map((entry, index) => (
                    <Cell key={entry.name} fill={colors[index % colors.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} itemStyle={{ color: "#f5f5f5" }} />
              </PieChart>
            ) : type === "line" ? (
              <LineChart data={data} margin={{ top: 12, right: 12, bottom: 8, left: 0 }}>
                <CartesianGrid stroke={gridColor} vertical={false} />
                <XAxis dataKey="name" stroke={axisColor} tick={{ fontSize: 12, fill: axisColor }} tickLine={false} axisLine={false} minTickGap={12} height={36} />
                <YAxis stroke={axisColor} tick={{ fontSize: 12, fill: axisColor }} tickLine={false} axisLine={false} width={44} />
                <Tooltip contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} itemStyle={{ color: "#f5f5f5" }} />
                <Line type="monotone" dataKey="value" stroke="#ff4a4d" strokeWidth={3} dot={false} activeDot={{ r: 5, fill: "#ff4a4d", stroke: "#111114", strokeWidth: 2 }} />
              </LineChart>
            ) : (
              <BarChart data={data} margin={{ top: 12, right: 12, bottom: 8, left: 0 }}>
                <CartesianGrid stroke={gridColor} vertical={false} />
                <XAxis dataKey="name" stroke={axisColor} tick={{ fontSize: 12, fill: axisColor }} tickLine={false} axisLine={false} minTickGap={10} height={42} />
                <YAxis stroke={axisColor} tick={{ fontSize: 12, fill: axisColor }} tickLine={false} axisLine={false} width={44} />
                <Tooltip contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} itemStyle={{ color: "#f5f5f5" }} cursor={{ fill: "rgba(239,43,45,0.08)" }} />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  {data.map((entry, index) => (
                    <Cell key={entry.name} fill={colors[index % colors.length]} />
                  ))}
                </Bar>
              </BarChart>
            )}
          </ResponsiveContainer>
        )}
      </div>
    </GlowPanel>
  );
}
