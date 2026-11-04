import { RequireAuth } from "@/components/require-auth";

export default function OrdersLayout({ children }: LayoutProps<"/orders">) {
  return <RequireAuth>{children}</RequireAuth>;
}
