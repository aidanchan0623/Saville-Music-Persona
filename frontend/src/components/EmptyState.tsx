import { Music2 } from "lucide-react";
import { AnimatedPageTitle } from "./AnimatedPageTitle";

interface Props {
  title: string;
  body: string;
  action?: React.ReactNode;
  titleTag?: "h1" | "h2";
  titleAnimationKey?: string;
}

export function EmptyState({ title, body, action, titleTag = "h2", titleAnimationKey }: Props) {
  return (
    <section className="rounded-lg border border-dashed border-white/15 bg-white/[0.03] p-8 text-center">
      <Music2 className="mx-auto text-violet-200" size={36} />
      {titleTag === "h1" ? (
        <AnimatedPageTitle animationKey={titleAnimationKey ?? title} text={title} className="mt-4 text-xl font-semibold text-white" textAlign="center" />
      ) : (
        <h2 className="mt-4 text-xl font-semibold text-white">{title}</h2>
      )}
      <p className="mx-auto mt-2 max-w-2xl text-sm leading-6 text-mist">{body}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </section>
  );
}
