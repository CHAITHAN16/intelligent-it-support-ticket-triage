import { AuthGuard } from "@/components/auth-guard";

export default function AgentLayout({ children }: { children: React.ReactNode }) {
  return <AuthGuard allowedRoles={["AGENT"]}>{children}</AuthGuard>;
}
