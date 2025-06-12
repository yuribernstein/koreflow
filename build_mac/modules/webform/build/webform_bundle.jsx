import React from "react";
import { createRoot } from "react-dom/client";
import Wizard from "./Wizard.jsx"; 

const rootElement = document.getElementById("root");
const root = createRoot(rootElement);
const SUBMIT_URL = `/${window.MODULE_NAME}/${window.WORKFLOW_UID}/${window.STEP_ID}/submit`;
console.log(`config file: ${window.CONFIG_FILE}`);
const configPath = `configs/${window.CONFIG_FILE}`;


(async () => {  
  try {
    const configModule = await import(`/webform/${window.WORKFLOW_UID}/${window.STEP_ID}/${configPath}`);
    const config = configModule.default;

    const updatedSteps = config.steps.map(step => {
      if (step.type === "submit") {
        return {
          ...step,
          submitUrl: SUBMIT_URL
        };
      }
      return step;
    });

    const finalConfig = {
      ...config,
      steps: updatedSteps
    };

    root.render(<Wizard config={finalConfig} />);
  } catch (err) {
    console.error("Failed to load form_config.js", err);
    root.render(<div>Form failed to load. Check console.</div>);
  }
})();
