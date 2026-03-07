import { redirect } from 'next/navigation'

export default function Home() {
  // Server-side redirect — actual auth check happens client-side
  redirect('/login')
}
