import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Overview from './pages/Overview'
import Models from './pages/Models'
import Providers from './pages/Providers'
import Settings from './pages/Settings'

export default function App() {
  return (
    <div className="flex min-h-screen bg-theme-bg">
      <Sidebar />
      <main className="flex-1 p-6 md:p-10">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/models" element={<Models />} />
          <Route path="/providers" element={<Providers />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  )
}
