import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import LiveView from './pages/LiveView'
import Dashboard from './pages/Dashboard'
import Blacklist from './pages/Blacklist'
import Admin from './pages/Admin'
import Login from './pages/Login'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Layout />}>
        <Route index element={<LiveView />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="blacklist" element={<Blacklist />} />
        <Route path="admin" element={<Admin />} />
      </Route>
    </Routes>
  )
}

export default App
