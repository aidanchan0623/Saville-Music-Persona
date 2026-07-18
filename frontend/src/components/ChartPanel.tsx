import type { ChartPoint } from "../types/api";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const colors = ["#ef4444", "#dc2626", "#b91c1c", "#991b1b", "#f87171", "#7f1d1d", "#fecaca", "#451a1a"];

interface Props {
  title: string;
  data: ChartPoint[];
  type?: "bar" | "pie" | "line";
}

export function ChartPanel({ title, data, type = "bar" }: Props) {
  return (
    <section className="rounded-lg border border-white/10 bg-white/[0.035] p-5 shadow-[0_18px_60px_rgba(0,0,0,0.18)]">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-mist/60">Chart</p>
      <h3 className="mt-2 text-lg font-black text-white">{title}</h3>
      <div className="mt-4 h-72">
        {data.length === 0 ? (
          <div className="grid h-full place-items-center rounded-md border border-dashed border-white/10 bg-white/[0.03] px-4 text-center text-sm text-mist">Not enough reliable data for this chart yet.</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            {type === "pie" ? (
              <PieChart>
                <Pie data={data} dataKey="value" nameKey="name" innerRadius={54} outerRadius={96} paddingAngle={3}>
                  {data.map((entry, index) => (
                    <Cell key={entry.name} fill={colors[index % colors.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "#120909", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, color: "#fff" }} />
              </PieChart>
            ) : type === "line" ? (
              <LineChart data={data}>
                <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                <XAxis dataKey="name" stroke="#b8b0b0" tick={{ fontSize: 12 }} />
                <YAxis stroke="#b8b0b0" tick={{ fontSize: 12 }} />
                <Tooltip contentStyle={{ background: "#120909", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, color: "#fff" }} />
                <Line type="monotone" dataKey="value" stroke="#ef4444" strokeWidth={3} dot={{ r: 2, fill: "#fecaca" }} activeDot={{ r: 5, fill: "#ef4444" }} />
              </LineChart>
            ) : (
              <BarChart data={data}>
                <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                <XAxis dataKey="name" stroke="#b8b0b0" tick={{ fontSize: 12 }} />
                <YAxis stroke="#b8b0b0" tick={{ fontSize: 12 }} />
                <Tooltip contentStyle={{ background: "#120909", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, color: "#fff" }} />
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
    </section>
  );
}
