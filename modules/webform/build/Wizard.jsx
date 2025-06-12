import React, { useState, useEffect, useRef } from "react";
import { CSSTransition, TransitionGroup } from "react-transition-group";
import "../styles/Wizard.css";

import Spinner from './Spinner.jsx'; 

const iconImports = {
  leftIcon: "icons/LeftA.svg",
  rightIcon: "icons/RightA.svg",
  doneIcon: "icons/Done.svg",
  searchCustomer: "icons/searchCustomer.svg",
  dataCenter: "icons/dataCenter.svg",
  Website: "icons/Website.svg",
  Jira: "icons/Jira.svg",
  Certificate: "icons/Certificate.svg"
};

const Wizard = ({ config }) => {
  const [currentStep, setCurrentStep] = useState(config.steps[0]);
  const [formData, setFormData] = useState({});
  const [history, setHistory] = useState([]);
  const [options, setOptions] = useState({});
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [dropdownVisible, setDropdownVisible] = useState(false);
  const [direction, setDirection] = useState("next");

  const searchInputRef = useRef(null);
  const dropdownRef = useRef(null);

  useEffect(() => {
    if (currentStep.apiFetch) {
      fetchApiOptions(currentStep);
    }
  }, [currentStep]);

  useEffect(() => {
    if (searchQuery.length > 0) {
      setDropdownVisible(true);
    } else {
      setDropdownVisible(false);
    }
  }, [searchQuery]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target) &&
        searchInputRef.current &&
        !searchInputRef.current.contains(event.target)
      ) {
        setDropdownVisible(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const fetchApiOptions = async (step) => {
    setLoading(true);
    try {
      const response = await fetch(step.apiFetch);
      if (!response.ok) throw new Error("API request failed");

      const data = await response.json();
      const extractedOptions = extractOptionsFromResponse(data, step.responsePath);
      setOptions((prev) => ({ ...prev, [step.id]: extractedOptions }));
    } catch (error) {
      console.error(`API fetch error for step ${step.id}:`, error);
      setOptions((prev) => ({ ...prev, [step.id]: [] }));
    } finally {
      setLoading(false);
    }
  };

  const extractOptionsFromResponse = (data, path) => {
    let extracted = data;
    if (path) {
      const pathParts = path.split(".");
      for (const part of pathParts) {
        if (extracted && extracted[part]) {
          extracted = extracted[part];
        } else {
          return [];
        }
      }
    }
    return Array.isArray(extracted) ? extracted : Object.keys(extracted);
  };

  const handleApiTrigger = async () => {
    if (currentStep.type !== "api-trigger") return;
    setLoading(true);
    const payloadField = currentStep.payloadField;
    const requestBody = payloadField ? { [payloadField]: formData[payloadField] } : formData;

    try {
      const response = await fetch(currentStep.apiCall, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });

      const nextStep = response.ok
        ? config.steps.find((step) => step.id === currentStep.successNextStep)
        : config.steps.find((step) => step.id === currentStep.failureNextStep);

      if (nextStep) {
        setHistory((prev) => [...prev, currentStep]);
        setCurrentStep(nextStep);
      } else {
        alert("API request failed.");
      }
    } catch (error) {
      console.error("API trigger error:", error);
      alert("Error triggering API.");
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setSearchQuery(value);
  };

  const handleMultiInputChange = (field, index, value) => {
    setFormData((prev) => {
      const updatedArray = [...(prev[field] || [])];
      updatedArray[index] = value;
      return { ...prev, [field]: updatedArray };
    });
  };

  const handleAddMultiInput = (field, maxInputs) => {
    setFormData((prev) => {
      const updatedArray = [...(prev[field] || [])];
      if (updatedArray.length < maxInputs) {
        updatedArray.push("");
      }
      return { ...prev, [field]: updatedArray };
    });
  };

  const handleRemoveMultiInput = (field, index) => {
    setFormData((prev) => {
      const updatedArray = [...(prev[field] || [])];
      updatedArray.splice(index, 1);
      return { ...prev, [field]: updatedArray };
    });
  };

  const handleSelectOption = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setSearchQuery(value);
    setDropdownVisible(false);
  };

  const handleNext = (selectedOption = null) => {
    let nextStepId = currentStep.nextStep || formData[currentStep.id]?.nextStep;

    if (currentStep.type === "junction" && selectedOption) {
      nextStepId = selectedOption.nextStep;
      handleChange(currentStep.id, selectedOption.label);
    }

    const nextStep = config.steps.find((step) => step.id === nextStepId);
    if (nextStep) {
      setDirection("next");
      setHistory((prev) => [...prev, currentStep]);
      setCurrentStep(nextStep);
    }
  };

  const handleBack = () => {
    if (history.length > 0) {
      const prevStep = history[history.length - 1];
      setDirection("back");
      setHistory(history.slice(0, -1));
      setCurrentStep(prevStep);
    }
  };

  const handleSubmit = async () => {
    if (currentStep.type === "submit") {
      try {
        const response = await fetch(currentStep.submitUrl, {
          method: "POST",
          headers: currentStep.headers,
          body: JSON.stringify(formData)
        });
        response.ok ? alert("Form submitted successfully!") : alert("Error submitting form.");
        window.close(); // if later we want to redirect to a thankyou page: window.location.href = "/thanks.html";
      } catch (error) {
        console.error("Submit error:", error);
        alert("Error submitting form.");
      }
    }
  };

  const renderStepLabel = (step) => (
    <span className="step-label">
      {step.iconName && <img src={iconImports[step.iconName]} alt={step.iconName} className="step-icon" />}
      {step.label || step.question}
    </span>
  );

  return (
    <div className="wizard-container">
      <TransitionGroup>
        <CSSTransition key={currentStep.id} timeout={300} classNames={direction}>
          <div className="wizard-step">
            <h2>{renderStepLabel(currentStep)}</h2>
            {currentStep.type === "api-trigger" && (
              <>
                <Spinner visible={loading} />
                <button onClick={handleApiTrigger}>Check</button>
              </>
            )}
            {currentStep.type === "info" && (
              <div className="info-step">
                <p>{currentStep.text}</p>
                <button onClick={handleNext}>Next</button>
              </div>
            )}
            {currentStep.type === "multiinput" && (
              <div className="multiinput-container">
                {(formData[currentStep.id] || []).map((value, index) => (
                  <div key={index} className="multiinput-row">
                    <input type="text" value={value} onChange={(e) => handleMultiInputChange(currentStep.id, index, e.target.value)} />
                    <button onClick={() => handleRemoveMultiInput(currentStep.id, index)}>➖</button>
                  </div>
                ))}
                {(formData[currentStep.id]?.length || 0) < currentStep.max_inputs && (
                  <button onClick={() => handleAddMultiInput(currentStep.id, currentStep.max_inputs)}>➕</button>
                )}
              </div>
            )}
            {currentStep.type === "junction" && (
              <div className="button-group">
                {currentStep.options.map((option) => (
                  <button key={option.label} onClick={() => handleNext(option)}>
                    {renderStepLabel(option)}
                  </button>
                ))}
              </div>
            )}
            {currentStep.type === "searchable-dropdown" && (
              <div className="searchable-dropdown">
                <Spinner visible={loading} />
                {loading ? (
                  <p>Loading customers...</p>
                ) : (
                  <div>
                    <input
                      ref={searchInputRef}
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search for a customer..."
                      onFocus={() => setDropdownVisible(true)}
                    />
                    {dropdownVisible && (
                      <ul ref={dropdownRef} className="dropdown-list">
                        {options[currentStep.id]?.filter((opt) =>
                          opt.toLowerCase().includes(searchQuery.toLowerCase())
                        ).map((opt) => (
                          <li key={opt} onClick={() => handleSelectOption(currentStep.id, opt)} className="dropdown-item">
                            {opt}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            )}
            {currentStep.type === "dropdown" && (
              <select onChange={(e) => handleChange(currentStep.id, e.target.value)} value={formData[currentStep.id] || ""}>
                <option value="" disabled>Select an option</option>
                {currentStep.options?.map((opt) => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            )}
            {currentStep.type === "input" && (
              <input
                type="text"
                placeholder={currentStep.label}
                value={formData[currentStep.id] || ""}
                onChange={(e) => handleChange(currentStep.id, e.target.value)}
              />
            )}
            {currentStep.type === "textbox" && (
              <textarea
                placeholder={currentStep.label}
                value={formData[currentStep.id] || ""}
                onChange={(e) => handleChange(currentStep.id, e.target.value)}
              />
            )}
            {currentStep.type === "submit" && <img src={iconImports.doneIcon} onClick={handleSubmit} />}
            <div className="wizard-buttons">
              {history.length > 0 && <img src={iconImports.leftIcon} onClick={handleBack} alt="Back" className="nav-icon" />}
              {currentStep.type !== "submit" && currentStep.type !== "junction" && (
                <img src={iconImports.rightIcon} onClick={handleNext} alt="Next" className="nav-icon" />
              )}
            </div>
          </div>
        </CSSTransition>
      </TransitionGroup>

      <footer className="wizard-footer">
      <a href="https://seyoawe.com" target="_blank" rel="noopener noreferrer" className="footer-link">
        <img src="icons/logo.jpg" alt="SeyoAWE Logo" className="footer-logo" />
        <span>Powered by SeyoAWE</span>
      </a>
    </footer>


    </div>
  );
};

export default Wizard;