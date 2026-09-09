import { AuthGuard } from "@/components/auth-guard";

export default function AgentLayout({ children }: LayoutProps<"/agent">) {
  return <AuthGuard allowedRoles={["AGENT"]}>{children}</AuthGuard>;
}
