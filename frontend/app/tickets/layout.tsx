import { AuthGuard } from "@/components/auth-guard";

export default function TicketsLayout({ children }: LayoutProps<"/tickets">) {
  return <AuthGuard allowedRoles={["EMPLOYEE"]}>{children}</AuthGuard>;
}
