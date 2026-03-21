import { mount } from 'svelte'
import './global.css'
import App from './App.svelte'
import './db'

const app = mount(App, {target: document.getElementById('app')})

export default app
