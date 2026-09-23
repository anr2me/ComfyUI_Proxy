import { app } from "../../scripts/app.js";

const CONFIG_ENDPOINT = "/cloud_redirect/config";

app.registerExtension({
    name: "Comfy.CloudRedirect",
    async setup() {
        let currentUrl = "";
        try {
            const resp = await fetch(CONFIG_ENDPOINT);
            if (resp.ok) {
                const data = await resp.json();
                currentUrl = data.cloud_url || "";
            }
        } catch (e) {
            console.error("[CloudRedirect] Failed to load current config", e);
        }

        app.ui.settings.addSetting({
            id: "CloudRedirect.CloudGpuUrl",
            name: "Cloud GPU URL",
            tooltip:
                "When set, /prompt and /queue requests are forwarded to this " +
                "server instead of running locally. Leave empty to run locally. " +
                "Example: https://my-cloud-gpu.example.com",
            type: "text",
            defaultValue: currentUrl,
            onChange: async (value) => {
                try {
                    const resp = await fetch(CONFIG_ENDPOINT, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ cloud_url: value }),
                    });
                    if (!resp.ok) {
                        throw new Error(`Server responded ${resp.status}`);
                    }
                    console.log(
                        `[CloudRedirect] Cloud GPU URL set to: ${value || "(none, running locally)"}`
                    );
                } catch (e) {
                    console.error("[CloudRedirect] Failed to save cloud GPU URL", e);
                    alert("Failed to save Cloud GPU URL: " + e.message);
                }
            },
        });
    },
});
