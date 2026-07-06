import type { ChartPoint } from "../types/api";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const colors = ["#8b5cf6", "#6366f1", "#d946ef", "#22d3ee", "#f59e0b", "#34d399", "#f472b6", "#a3e635"];

interface Props {
  title: string;
  data: ChartPoint[];
  type?: "bar" | "pie" | "line";
}

export function ChartPanel({ title, data, type = "bar" }: Props) {
  return (
    <section className="rounded-lg border border-line bg-panel/80 p-5">
      <h3 className="text-lg font-semibold text-white">{title}</h3>
      <div className="mt-4 h-72">
        {data.length === 0 ? (
          <div className="grid h-full place-items-center rounded-md bg-white/[0.03] text-sm text-mist">Not enough reliable data for this chart yet.</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            {type === "pie" ? (
              <PieChart>
                <Pie data={data} dataKey="value" nameKey="name" innerRadius={54} outerRadius={96} paddingAngle={3}>
                  {data.map((entry, index) => (
                    <Cell key={entry.name} fill={colors[index % colors.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "#11111d", border: "1px solid rgba(255,255,255,0.12)", color: "#fff" }} />
              </PieChart>
            ) : type === "line" ? (
              <LineChart data={data}>
                <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                <XAxis dataKey="name" stroke="#c7c4dc" tick={{ fontSize: 12 }} />
                <YAxis stroke="#c7c4dc" tick={{ fontSize: 12 }} />
                <Tooltip contentStyle={{ background: "#11111d", border: "1px solid rgba(255,255,255,0.12)", color: "#fff" }} />
                <Line type="monotone" dataKey="value" stroke="#a78bfa" strokeWidth={3} dot={false} />
              </LineChart>
            ) : (
              <BarChart data={data}>
                <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                <XAxis dataKey="name" stroke="#c7c4dc" tick={{ fontSize: 12 }} />
                <YAxis stroke="#c7c4dc" tick={{ fontSize: 12 }} />
                <Tooltip contentStyle={{ background: "#11111d", border: "1px solid rgba(255,255,255,0.12)", color: "#fff" }} />
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

