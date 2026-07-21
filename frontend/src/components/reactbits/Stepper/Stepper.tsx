import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import type { ButtonHTMLAttributes, CSSProperties, ReactNode } from "react";
import { Children, Fragment, useCallback, useLayoutEffect, useRef, useState } from "react";
import "./Stepper.css";

type StepperProps = {
  children: ReactNode;
  initialStep?: number;
  onStepChange?: (step: number) => void;
  onFinalStepCompleted?: () => void;
  stepCircleContainerClassName?: string;
  stepContainerClassName?: string;
  contentClassName?: string;
  footerClassName?: string;
  backButtonProps?: ButtonHTMLAttributes<HTMLButtonElement>;
  nextButtonProps?: ButtonHTMLAttributes<HTMLButtonElement>;
  backButtonText?: string;
  nextButtonText?: string;
  completeButtonText?: string;
  completeAction?: "complete" | "restart";
  disableStepIndicators?: boolean;
  renderStepIndicator?: (props: { step: number; currentStep: number; onStepClick: (step: number) => void }) => ReactNode;
  stepLabels?: string[];
  className?: string;
  style?: CSSProperties;
};

type StepContentWrapperProps = {
  isCompleted: boolean;
  currentStep: number;
  direction: number;
  children: ReactNode;
  className: string;
};

type SlideTransitionProps = {
  children: ReactNode;
  direction: number;
  reduceMotion: boolean;
  onHeightReady: (height: number) => void;
};

export default function Stepper({
  children,
  initialStep = 1,
  onStepChange = () => {},
  onFinalStepCompleted = () => {},
  stepCircleContainerClassName = "",
  stepContainerClassName = "",
  contentClassName = "",
  footerClassName = "",
  backButtonProps = {},
  nextButtonProps = {},
  backButtonText = "Back",
  nextButtonText = "Continue",
  completeButtonText = "Complete",
  completeAction = "complete",
  disableStepIndicators = false,
  renderStepIndicator,
  stepLabels = [],
  className = "",
  style,
  ...rest
}: StepperProps) {
  const [currentStep, setCurrentStep] = useState(initialStep);
  const [direction, setDirection] = useState(0);
  const stepsArray = Children.toArray(children);
  const totalSteps = stepsArray.length;
  const isCompleted = currentStep > totalSteps;
  const isLastStep = currentStep === totalSteps;

  const updateStep = useCallback(
    (newStep: number) => {
      setCurrentStep(newStep);
      if (newStep > totalSteps) {
        onFinalStepCompleted();
      } else {
        onStepChange(newStep);
      }
    },
    [onFinalStepCompleted, onStepChange, totalSteps],
  );

  const handleBack = () => {
    if (currentStep > 1) {
      setDirection(-1);
      updateStep(currentStep - 1);
    }
  };

  const handleNext = () => {
    if (!isLastStep) {
      setDirection(1);
      updateStep(currentStep + 1);
    }
  };

  const handleComplete = () => {
    onFinalStepCompleted();
    if (completeAction === "restart") {
      setDirection(-1);
      updateStep(1);
      return;
    }
    setDirection(1);
    setCurrentStep(totalSteps + 1);
  };

  return (
    <div className={`smp-stepper${className ? ` ${className}` : ""}`} style={style} {...rest}>
      <div className={`smp-stepper__shell ${stepCircleContainerClassName}`}>
        <div className={`smp-stepper__indicator-row ${stepContainerClassName}`} aria-label="Overview sections">
          {stepsArray.map((_, index) => {
            const stepNumber = index + 1;
            const isNotLastStep = index < totalSteps - 1;
            return (
              <Fragment key={stepNumber}>
                {renderStepIndicator ? (
                  renderStepIndicator({
                    step: stepNumber,
                    currentStep,
                    onStepClick: (clicked) => {
                      setDirection(clicked > currentStep ? 1 : -1);
                      updateStep(clicked);
                    },
                  })
                ) : (
                  <StepIndicator
                    step={stepNumber}
                    label={stepLabels[index]}
                    disableStepIndicators={disableStepIndicators}
                    currentStep={currentStep}
                    onClickStep={(clicked) => {
                      setDirection(clicked > currentStep ? 1 : -1);
                      updateStep(clicked);
                    }}
                  />
                )}
                {isNotLastStep ? <StepConnector isComplete={currentStep > stepNumber} /> : null}
              </Fragment>
            );
          })}
        </div>

        <StepContentWrapper isCompleted={isCompleted} currentStep={currentStep} direction={direction} className={`smp-stepper__content ${contentClassName}`}>
          {stepsArray[currentStep - 1]}
        </StepContentWrapper>

        {!isCompleted ? (
          <div className={`smp-stepper__footer ${footerClassName}`}>
            <div className={`smp-stepper__footer-nav ${currentStep !== 1 ? "smp-stepper__footer-nav--spread" : "smp-stepper__footer-nav--end"}`}>
              {currentStep !== 1 ? (
                <button type="button" onClick={handleBack} className="smp-stepper__back-button" {...backButtonProps}>
                  {backButtonText}
                </button>
              ) : null}
              <button type="button" onClick={isLastStep ? handleComplete : handleNext} className="smp-stepper__next-button" {...nextButtonProps}>
                {isLastStep ? completeButtonText : nextButtonText}
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function StepContentWrapper({ isCompleted, currentStep, direction, children, className }: StepContentWrapperProps) {
  const [parentHeight, setParentHeight] = useState(0);
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      className={className}
      style={{ position: "relative", overflow: "hidden" }}
      animate={{ height: isCompleted ? 0 : parentHeight }}
      transition={reduceMotion ? { duration: 0 } : { type: "spring", duration: 0.36, bounce: 0.12 }}
    >
      <AnimatePresence initial={false} mode="sync" custom={direction}>
        {!isCompleted ? (
          <SlideTransition key={currentStep} direction={direction} reduceMotion={Boolean(reduceMotion)} onHeightReady={(height) => setParentHeight(height)}>
            {children}
          </SlideTransition>
        ) : null}
      </AnimatePresence>
    </motion.div>
  );
}

function SlideTransition({ children, direction, reduceMotion, onHeightReady }: SlideTransitionProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useLayoutEffect(() => {
    const node = containerRef.current;
    if (!node) return;

    const updateHeight = () => onHeightReady(node.offsetHeight);
    updateHeight();

    const observer = typeof ResizeObserver !== "undefined" ? new ResizeObserver(updateHeight) : null;
    observer?.observe(node);

    if (document.fonts?.ready) {
      void document.fonts.ready.then(updateHeight);
    }

    window.addEventListener("resize", updateHeight);
    return () => {
      observer?.disconnect();
      window.removeEventListener("resize", updateHeight);
    };
  }, [children, onHeightReady]);

  return (
    <motion.div
      ref={containerRef}
      custom={direction}
      variants={stepVariants}
      initial={reduceMotion ? "center" : "enter"}
      animate="center"
      exit={reduceMotion ? "center" : "exit"}
      transition={reduceMotion ? { duration: 0 } : { duration: 0.32, ease: "easeOut" }}
      style={{ position: "absolute", left: 0, right: 0, top: 0 }}
    >
      {children}
    </motion.div>
  );
}

const stepVariants = {
  enter: (direction: number) => ({
    x: direction >= 0 ? "-100%" : "100%",
    opacity: 0,
  }),
  center: {
    x: "0%",
    opacity: 1,
  },
  exit: (direction: number) => ({
    x: direction >= 0 ? "42%" : "-42%",
    opacity: 0,
  }),
};

export function Step({ children }: { children: ReactNode }) {
  return <div className="smp-stepper__step">{children}</div>;
}

function StepIndicator({
  step,
  label,
  currentStep,
  onClickStep,
  disableStepIndicators,
}: {
  step: number;
  label?: string;
  currentStep: number;
  onClickStep: (step: number) => void;
  disableStepIndicators: boolean;
}) {
  const status = currentStep === step ? "active" : currentStep < step ? "inactive" : "complete";

  const handleClick = () => {
    if (step !== currentStep && !disableStepIndicators) onClickStep(step);
  };

  return (
    <motion.button
      type="button"
      onClick={handleClick}
      className="smp-stepper__indicator"
      disabled={disableStepIndicators}
      data-status={status}
      animate={status}
      initial={false}
      aria-current={status === "active" ? "step" : undefined}
      aria-label={label ? `Go to ${label}` : `Go to step ${step}`}
    >
      <motion.span
        variants={{
          inactive: { scale: 1 },
          active: { scale: 1 },
          complete: { scale: 1 },
        }}
        transition={{ duration: 0.2 }}
        className="smp-stepper__indicator-dot"
      >
        {status === "complete" ? <CheckIcon className="smp-stepper__check-icon" /> : <span>{step}</span>}
      </motion.span>
      {label ? <span className="smp-stepper__indicator-label">{label}</span> : null}
    </motion.button>
  );
}

function StepConnector({ isComplete }: { isComplete: boolean }) {
  return (
    <span className="smp-stepper__connector" aria-hidden="true">
      <motion.span
        className="smp-stepper__connector-inner"
        initial={false}
        animate={isComplete ? { width: "100%" } : { width: 0 }}
        transition={{ duration: 0.25 }}
      />
    </span>
  );
}

function CheckIcon(props: { className?: string }) {
  return (
    <svg {...props} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
      <motion.path
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ delay: 0.05, type: "tween", ease: "easeOut", duration: 0.24 }}
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M5 13l4 4L19 7"
      />
    </svg>
  );
}
