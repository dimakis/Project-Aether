import { useMemo, type ComponentPropsWithoutRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CodeBlock, InlineCode } from "@/components/ui/code-block";
import { cn } from "@/lib/utils";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

/** Custom markdown renderer that routes code blocks to shiki CodeBlock component */
export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  const components = useMemo(() => ({
    // Route fenced code blocks through our shiki CodeBlock
    code(props: ComponentPropsWithoutRef<"code">) {
      const { children, className: codeClassName, ...rest } = props;
      const match = /language-(\w+)/.exec(codeClassName || "");

      // If it has a language class, it's a fenced code block (inside <pre>)
      if (match) {
        const lang = match[1];
        const codeStr = String(children).replace(/\n$/, "");
        return (
          <CodeBlock
            code={codeStr}
            language={lang}
            collapsible={codeStr.split("\n").length > 30}
          />
        );
      }

      // Inline code
      return <InlineCode>{children}</InlineCode>;
    },

    // Override <pre> to avoid double-wrapping when CodeBlock is used
    pre(props: ComponentPropsWithoutRef<"pre">) {
      const { children } = props;
      // If children is our CodeBlock, don't wrap in <pre>
      return <>{children}</>;
    },

    // Enhanced table styling
    table(props: ComponentPropsWithoutRef<"table">) {
      return (
        <div className="my-4 overflow-x-auto rounded-lg border border-border/50">
          <table className="w-full text-sm" {...props} />
        </div>
      );
    },
    thead(props: ComponentPropsWithoutRef<"thead">) {
      return <thead className="border-b border-border/50 bg-muted/30" {...props} />;
    },
    th(props: ComponentPropsWithoutRef<"th">) {
      return (
        <th
          className="px-4 py-2 text-left text-xs font-semibold text-muted-foreground"
          {...props}
        />
      );
    },
    td(props: ComponentPropsWithoutRef<"td">) {
      return (
        <td
          className="border-t border-border/30 px-4 py-2 text-sm"
          {...props}
        />
      );
    },

    // Enhanced blockquote
    blockquote(props: ComponentPropsWithoutRef<"blockquote">) {
      return (
        <blockquote
          className="my-3 border-l-2 border-primary/40 pl-4 text-muted-foreground italic"
          {...props}
        />
      );
    },

    // Enhanced links
    a(props: ComponentPropsWithoutRef<"a">) {
      return (
        <a
          className="text-primary underline decoration-primary/30 underline-offset-2 transition-colors hover:decoration-primary"
          target="_blank"
          rel="noopener noreferrer"
          {...props}
        />
      );
    },

    // Enhanced headings
    h1(props: ComponentPropsWithoutRef<"h1">) {
      return <h1 className="mb-4 mt-6 text-xl font-bold first:mt-0" {...props} />;
    },
    h2(props: ComponentPropsWithoutRef<"h2">) {
      return <h2 className="mb-3 mt-5 text-lg font-semibold first:mt-0" {...props} />;
    },
    h3(props: ComponentPropsWithoutRef<"h3">) {
      return <h3 className="mb-2 mt-4 text-base font-semibold first:mt-0" {...props} />;
    },

    // Enhanced lists
    ul(props: ComponentPropsWithoutRef<"ul">) {
      return <ul className="my-2 ml-1 list-none space-y-1" {...props} />;
    },
    ol(props: ComponentPropsWithoutRef<"ol">) {
      return <ol className="my-2 ml-1 list-decimal space-y-1 pl-4" {...props} />;
    },
    li(props: ComponentPropsWithoutRef<"li">) {
      const { children, ...rest } = props;
      return (
        <li className="relative pl-5 text-sm leading-relaxed" {...rest}>
          <span className="absolute left-0 top-[0.45em] h-1.5 w-1.5 rounded-full bg-primary/40" />
          {children}
        </li>
      );
    },

    // Paragraphs
    p(props: ComponentPropsWithoutRef<"p">) {
      return <p className="my-2 text-sm leading-relaxed first:mt-0 last:mb-0" {...props} />;
    },

    // Horizontal rule
    hr() {
      return <hr className="my-6 border-border/50" />;
    },

    // Strong / emphasis
    strong(props: ComponentPropsWithoutRef<"strong">) {
      return <strong className="font-semibold text-foreground" {...props} />;
    },
  }), []);

  return (
    <div className={cn("markdown-body", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
