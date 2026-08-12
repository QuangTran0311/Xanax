import { type FormEvent, useEffect, useRef, useState } from "react";

import { ApiError } from "../../api/client";
import { Icon } from "../../components/Icon";
import { sessionApi } from "../../store/session";
import { useTheme } from "../../store/theme";
import styles from "./LoginPage.module.css";

const IDLE_MESSAGE = "Phiên làm việc đã hết hạn do không có thao tác. Vui lòng đăng nhập lại.";

export function LoginPage() {
  const { theme, toggleTheme } = useTheme();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(() =>
    new URLSearchParams(window.location.search).get("reason") === "idle" ? IDLE_MESSAGE : "",
  );
  const [shake, setShake] = useState(false);
  const usernameRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const shakeTimer = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (shakeTimer.current !== null) {
        window.clearTimeout(shakeTimer.current);
      }
    },
    [],
  );

  function showError(message: string) {
    setError(message);
    setShake(false);
    window.requestAnimationFrame(() => setShake(true));
    if (shakeTimer.current !== null) {
      window.clearTimeout(shakeTimer.current);
    }
    shakeTimer.current = window.setTimeout(() => setShake(false), 400);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) return;

    const cleanUsername = username.trim();
    if (!cleanUsername) {
      showError("Vui lòng nhập tài khoản.");
      usernameRef.current?.focus();
      return;
    }
    if (!password) {
      showError("Vui lòng nhập mật khẩu.");
      passwordRef.current?.focus();
      return;
    }

    setError("");
    setLoading(true);
    try {
      await sessionApi.login({ username: cleanUsername, password });
      // Login is now a standalone route in the single React app. A normal
      // window navigation is correct; there is no parent frame to escape.
      window.location.assign("/hub");
    } catch (caught) {
      showError(
        caught instanceof ApiError
          ? caught.message
          : "Không thể kết nối đến máy chủ. Vui lòng thử lại.",
      );
    } finally {
      setLoading(false);
    }
  }

  const themeLabel =
    theme === "light" ? "Chuyển sang giao diện tối" : "Chuyển sang giao diện sáng";

  return (
    <>
      <div className={styles.root}>
        <section className={styles["panel-left"]}>
          <i className={`${styles["welcome-shape"]} ${styles["shape-a"]}`} aria-hidden="true" />
          <i className={`${styles["welcome-shape"]} ${styles["shape-b"]}`} aria-hidden="true" />
          <div className={styles.wordmark}>
            <span className={styles.dot} />
            <span>Xanax</span>
          </div>

          <div className={styles.hero}>
            <div className={styles.eyebrow}>
              <div className={styles["eyebrow-tag"]}>Xây dựng trên</div>
              <div className={styles["eyebrow-sub"]}>Hạ tầng hiệu năng cao, điều phối bởi AI</div>
            </div>
            <div className={styles["cards-row"]}>
              <div className={styles["card-antigravity"]}>
                <div className={styles["card-img-wrap-a"]}>
                  <img src="/images/antigravity.png" className={styles["card-img-a"]} alt="Antigravity" />
                </div>
                <div className={styles["card-info"]}>
                  <div className={styles["card-name"]}>Antigravity</div>
                  <div className={styles["card-desc"]}>Runtime platform</div>
                </div>
                <div className={styles["badge-cyan"]}>Core Engine</div>
              </div>
              <div className={styles.connector} aria-hidden="true">
                <div className={styles["connector-line-v"]} />
                <div className={styles["connector-h"]}>
                  <div className={styles["connector-dash"]} />
                  <div className={styles["connector-dot"]} />
                  <div className={styles["connector-dash"]} />
                </div>
                <div className={styles["connector-line-v"]} />
              </div>
              <div className={styles["card-hermes"]}>
                <div className={styles["card-img-wrap-h"]}>
                  <img src="/images/hermes.png" className={styles["card-img-h"]} alt="Hermes Agent" />
                </div>
                <div className={styles["card-info"]}>
                  <div className={styles["card-name"]}>Hermes Agent</div>
                  <div className={styles["card-desc"]}>AI agent framework</div>
                </div>
                <div className={styles["badge-purple"]}>AI Engine</div>
              </div>
            </div>
          </div>
        </section>

        <div className={styles["neon-divider"]} />

        <main className={styles["panel-right"]}>
          <button
            type="button"
            className={styles["theme-toggle"]}
            onClick={toggleTheme}
            aria-label={themeLabel}
            title={themeLabel}
          >
            <Icon name={theme === "light" ? "moon" : "sun"} />
          </button>
          <div className={styles["form-wrap"]}>
            <div className={styles["form-header"]}>
              <div className={styles["form-eyebrow"]}>
                <img src="/images/xanax.png" alt="Xanax" /> Xanax
              </div>
              <h1 className={styles["form-title"]}>Đăng nhập</h1>
              <p className={styles["form-sub"]}>Truy cập hệ thống quản lý</p>
            </div>
            <form
              className={`${styles.fields} ${shake ? styles.shake : ""}`}
              onSubmit={handleSubmit}
              noValidate
            >
              <div className={styles.field}>
                <label className={styles["field-label"]} htmlFor="username">Tài khoản</label>
                <div className={styles["field-wrap"]}>
                  <Icon name="user" className={styles["field-icon"]} size={16} strokeWidth={1.5} />
                  <input
                    ref={usernameRef}
                    id="username"
                    type="text"
                    className={styles["field-input"]}
                    placeholder="Nhập tài khoản..."
                    autoComplete="username"
                    autoCorrect="off"
                    autoCapitalize="off"
                    spellCheck={false}
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                  />
                </div>
              </div>
              <div className={styles.field}>
                <label className={styles["field-label"]} htmlFor="password">Mật khẩu</label>
                <div className={styles["field-wrap"]}>
                  <Icon name="loginLock" className={styles["field-icon"]} size={16} strokeWidth={1.5} />
                  <input
                    ref={passwordRef}
                    id="password"
                    type={showPassword ? "text" : "password"}
                    className={`${styles["field-input"]} ${styles["has-toggle"]}`}
                    placeholder="Nhập mật khẩu..."
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                  />
                  <button
                    type="button"
                    className={styles["toggle-btn"]}
                    aria-label="Hiện/ẩn mật khẩu"
                    onClick={() => setShowPassword((current) => !current)}
                  >
                    <Icon name={showPassword ? "eyeOff" : "eye"} size={16} strokeWidth={1.5} />
                  </button>
                </div>
              </div>
              <div className={styles.forgot}><a href="#">Quên mật khẩu?</a></div>
              <div
                className={`${styles["error-msg"]} ${error ? styles.visible : ""}`}
                role="alert"
                aria-live="polite"
              >
                {error}
              </div>
              <button type="submit" className={styles["submit-btn"]} disabled={loading}>
                <span>{loading ? "Đang xác thực..." : "Đăng nhập"}</span>
                {loading ? <span className={styles.spinner} aria-hidden="true" /> : <Icon name="loginArrow" size={16} strokeWidth={2} />}
              </button>
            </form>
          </div>
          <div className={styles["panel-footer"]}>v1.0 · Antigravity × Hermes Agent</div>
        </main>
      </div>

      <footer className={styles["page-footer"]}>© 2025 Xanax — Personal AI Agent</footer>
    </>
  );
}
