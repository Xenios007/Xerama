import { useEffect, useState } from "react";
import { Button } from "../components/ui/Button";
import { QueryState } from "../components/ui/QueryState";
import { useChatStatus, useSettings, useUpdateSettings } from "../api/queries";
import type { SettingsUpdateRequest } from "../api/types";
import "./SettingsPage.css";

type SectionId = "story" | "media" | "assistant" | "other";

const SECTIONS: { id: SectionId; label: string }[] = [
  { id: "story", label: "Story / Script" },
  { id: "media", label: "Image & Video" },
  { id: "assistant", label: "Assistant" },
  { id: "other", label: "Other" },
];

/**
 * Settings, laid out as a sidebar-nav + grouped-panels page - the pattern
 * follows the user's other project (MangaTranslator's Config tab): a left
 * list of section buttons, one section's panel visible at a time on the
 * right, a single Save action for the whole form. Only the video-relevant
 * subset of that pattern is kept here (provider choice + conditional
 * per-provider fields) - not the manga-specific settings (OCR, bubble
 * detection, hyphenation, font packs).
 */
export function SettingsPage() {
  const settings = useSettings();
  const chatStatus = useChatStatus();
  const update = useUpdateSettings();
  const [section, setSection] = useState<SectionId>("story");

  const [llmProvider, setLlmProvider] = useState<"openrouter" | "ollama">("openrouter");
  const [ollamaModel, setOllamaModel] = useState("");
  const [ollamaBaseUrl, setOllamaBaseUrl] = useState("");
  const [mediaProvider, setMediaProvider] = useState<"fal" | "fake">("fake");
  const [chatModel, setChatModel] = useState("");

  // Seed local form state once the server value first arrives - after that,
  // the form is the source of truth until Save round-trips a fresh value.
  useEffect(() => {
    if (!settings.data) return;
    setLlmProvider(settings.data.runtime.llm_provider);
    setOllamaModel(settings.data.runtime.ollama_model);
    setOllamaBaseUrl(settings.data.runtime.ollama_base_url);
    setMediaProvider(settings.data.runtime.media_provider);
    setChatModel(settings.data.runtime.chat_model);
  }, [settings.data]);

  function handleSave(event: React.FormEvent) {
    event.preventDefault();
    const payload: SettingsUpdateRequest = {
      llm_provider: llmProvider,
      chat_model: chatModel.trim(),
      ollama_model: ollamaModel.trim(),
      ollama_base_url: ollamaBaseUrl.trim(),
      media_provider: mediaProvider,
    };
    update.mutate(payload);
  }

  return (
    <div>
      <h1>Settings</h1>
      <p className="xr-settings__intro">
        Choose which providers generate story text and media. Changes apply immediately - no restart
        needed.
      </p>

      <QueryState isLoading={settings.isLoading} error={settings.error}>
        {settings.data && (
          <form onSubmit={handleSave}>
            <div className="xr-settings__toolbar">
              <Button type="submit" disabled={update.isPending}>
                Save
              </Button>
              {update.isSuccess && <span className="xr-settings__saved">Saved</span>}
              {update.isError && <span className="xr-settings__error">{update.error.message}</span>}
            </div>

            <div className="xr-settings__layout">
              <nav className="xr-settings__nav">
                {SECTIONS.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    className={`xr-settings__nav-button${section === s.id ? " xr-settings__nav-button--active" : ""}`}
                    onClick={() => setSection(s.id)}
                  >
                    {s.label}
                  </button>
                ))}
              </nav>

              <div className="xr-settings__content">
                {section === "story" && (
                  <div className="xr-settings__group">
                    <h3>Story / Script Generation</h3>
                    <label className="xr-settings__option">
                      <input
                        type="radio"
                        name="llm_provider"
                        checked={llmProvider === "openrouter"}
                        onChange={() => setLlmProvider("openrouter")}
                      />
                      <div>
                        <strong>OpenRouter</strong> - cloud models, per-role config from <code>.env</code>
                        <div className="xr-settings__status">
                          API key: {settings.data.openrouter_key_configured ? "configured" : "not configured"}
                        </div>
                      </div>
                    </label>
                    <label className="xr-settings__option">
                      <input
                        type="radio"
                        name="llm_provider"
                        checked={llmProvider === "ollama"}
                        onChange={() => setLlmProvider("ollama")}
                      />
                      <div>
                        <strong>Local (Ollama)</strong> - free, runs on this machine, one model for every
                        role
                        <div className="xr-settings__status">
                          {settings.data.ollama_reachable ? "Ollama is reachable" : "Ollama is not reachable"}
                        </div>
                      </div>
                    </label>

                    {llmProvider === "ollama" && (
                      <div className="xr-settings__fields">
                        <label>
                          Model
                          <input
                            value={ollamaModel}
                            onChange={(e) => setOllamaModel(e.target.value)}
                            placeholder="qwen2.5:7b"
                          />
                        </label>
                        <label>
                          Base URL
                          <input
                            value={ollamaBaseUrl}
                            onChange={(e) => setOllamaBaseUrl(e.target.value)}
                            placeholder="http://localhost:11434/v1"
                          />
                        </label>
                      </div>
                    )}
                  </div>
                )}

                {section === "media" && (
                  <div className="xr-settings__group">
                    <h3>Image &amp; Video Generation</h3>
                    <p className="xr-settings__hint">
                      One setting covers both - image keyframes and video takes come from the same
                      provider.
                    </p>
                    <label className="xr-settings__option">
                      <input
                        type="radio"
                        name="media_provider"
                        checked={mediaProvider === "fal"}
                        onChange={() => setMediaProvider("fal")}
                      />
                      <div>
                        <strong>fal.ai</strong> - real AI-generated images/video (paid, metered)
                        <div className="xr-settings__status">
                          API key: {settings.data.fal_key_configured ? "configured" : "not configured"}
                        </div>
                      </div>
                    </label>
                    <label className="xr-settings__option">
                      <input
                        type="radio"
                        name="media_provider"
                        checked={mediaProvider === "fake"}
                        onChange={() => setMediaProvider("fake")}
                      />
                      <div>
                        <strong>Placeholder</strong> - deterministic fake media, zero cost, for pipeline
                        testing
                      </div>
                    </label>
                  </div>
                )}

                {section === "assistant" && (
                  <div className="xr-settings__group">
                    <h3>Xerama Assistant</h3>
                    <p className="xr-settings__hint">
                      A chat panel (bottom-right of every page) for help with story concepts, shot
                      prompts, and creative direction. Rides your OpenRouter key - no separate
                      Anthropic key needed. Defaults to a Claude model, billed through OpenRouter
                      rather than a personal claude.ai login.
                    </p>
                    <div className="xr-settings__status">
                      OpenRouter key:{" "}
                      {chatStatus.isLoading
                        ? "checking…"
                        : chatStatus.data?.configured
                          ? "configured"
                          : "not configured (add OPENROUTER_API_KEY)"}
                    </div>
                    <div className="xr-settings__fields">
                      <label>
                        Model
                        <input
                          value={chatModel}
                          onChange={(e) => setChatModel(e.target.value)}
                          placeholder="anthropic/claude-sonnet-5"
                        />
                      </label>
                    </div>
                  </div>
                )}

                {section === "other" && (
                  <div className="xr-settings__group">
                    <h3>Other</h3>
                    <p className="xr-settings__hint">Nothing here yet.</p>
                  </div>
                )}
              </div>
            </div>
          </form>
        )}
      </QueryState>
    </div>
  );
}
