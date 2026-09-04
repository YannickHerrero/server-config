use std::env;
use std::error::Error;
use std::fs::{self, OpenOptions};
use std::io::{self, IsTerminal, Stdout};
use std::os::unix::fs::{OpenOptionsExt, PermissionsExt};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

use crossterm::event::{self, Event, KeyCode, KeyEvent, KeyEventKind};
use crossterm::execute;
use crossterm::terminal::{
    EnterAlternateScreen, LeaveAlternateScreen, disable_raw_mode, enable_raw_mode,
};
use ratatui::Frame;
use ratatui::Terminal;
use ratatui::backend::CrosstermBackend;
use ratatui::layout::{Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, List, ListItem, ListState, Paragraph, Wrap};

const APP_VERSION: &str = env!("CARGO_PKG_VERSION");
type Tui = Terminal<CrosstermBackend<Stdout>>;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum StepKind {
    Tailscale,
    GitHub,
    Vercel,
    Pi,
    Codex,
    GitIdentity,
    Convergence,
}

impl StepKind {
    const ALL: [Self; 7] = [
        Self::Tailscale,
        Self::GitHub,
        Self::Vercel,
        Self::Pi,
        Self::Codex,
        Self::GitIdentity,
        Self::Convergence,
    ];

    fn title(self) -> &'static str {
        match self {
            Self::Tailscale => "Tailscale",
            Self::GitHub => "GitHub CLI",
            Self::Vercel => "Vercel CLI",
            Self::Pi => "Pi provider",
            Self::Codex => "Codex CLI",
            Self::GitIdentity => "Git identity",
            Self::Convergence => "Server convergence",
        }
    }

    fn description(self) -> &'static str {
        match self {
            Self::Tailscale => {
                "Connect this host to the tailnet before private-access rules converge."
            }
            Self::GitHub => {
                "Authenticate gh for private repositories, pull requests, and Git HTTPS credentials."
            }
            Self::Vercel => "Authenticate the Vercel CLI before deploying projects from this host.",
            Self::Pi => "Start Pi, run /login, select a provider, then exit Pi to return here.",
            Self::Codex => {
                "Authenticate Codex with ChatGPT before pairing experimental Remote Control."
            }
            Self::GitIdentity => {
                "Store name and email in an ignored local file. Ansible applies them without changing gh credentials."
            }
            Self::Convergence => {
                "Run the dry-run, approve it, apply, prove changed=0, and run doctor."
            }
        }
    }

    fn command(self) -> Option<&'static str> {
        match self {
            Self::Tailscale => Some(
                "sudo tailscale up --hostname=\"$(hostname)\" --operator=\"$(id -un)\" --ssh=false",
            ),
            Self::GitHub => Some("gh auth login --hostname github.com --git-protocol https --web"),
            Self::Vercel => Some("vercel login"),
            Self::Pi => Some("pi"),
            Self::Codex => Some("codex login --device-auth"),
            Self::GitIdentity => None,
            Self::Convergence => Some("./bin/converge"),
        }
    }
}

#[derive(Clone, Debug, Default)]
struct StatusSnapshot {
    tailscale: bool,
    github: bool,
    vercel: bool,
    pi: bool,
    codex: bool,
    git_identity: bool,
    git_identity_saved: bool,
    convergence: bool,
}

impl StatusSnapshot {
    fn collect(root: &Path) -> Self {
        let git_identity_saved = valid_git_identity_file(&root.join("config/git/identity.local"));
        let git_identity = command_succeeds(
            "git",
            &["config", "--global", "--includes", "--get", "user.name"],
        ) && command_succeeds(
            "git",
            &["config", "--global", "--includes", "--get", "user.email"],
        );

        Self {
            tailscale: command_succeeds("tailscale", &["ip", "-4"]),
            github: command_succeeds("gh", &["auth", "status"]),
            vercel: command_succeeds("timeout", &["10", "vercel", "whoami"]),
            pi: pi_auth_is_present(),
            codex: command_succeeds("codex", &["login", "status"]),
            git_identity,
            git_identity_saved,
            convergence: convergence_is_current(root, git_identity_saved),
        }
    }

    fn complete(&self, step: StepKind) -> bool {
        match step {
            StepKind::Tailscale => self.tailscale,
            StepKind::GitHub => self.github,
            StepKind::Vercel => self.vercel,
            StepKind::Pi => self.pi,
            StepKind::Codex => self.codex,
            StepKind::GitIdentity => self.git_identity,
            StepKind::Convergence => self.convergence,
        }
    }

    fn completed_count(&self) -> usize {
        StepKind::ALL
            .iter()
            .filter(|step| self.complete(**step))
            .count()
    }

    fn detail(&self, step: StepKind) -> &'static str {
        if self.complete(step) {
            return "Complete. Press Enter to run this step again.";
        }
        if step == StepKind::GitIdentity && self.git_identity_saved {
            return "Saved locally. Run Server convergence to apply it.";
        }
        "Pending. Press Enter to start."
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Mode {
    Browse,
    EditName,
    EditEmail,
}

#[derive(Debug)]
enum Action {
    None,
    Quit,
    Refresh,
    Run(StepKind),
    SaveIdentity { name: String, email: String },
}

#[derive(Debug)]
struct App {
    selected: usize,
    mode: Mode,
    name: String,
    email: String,
    message: String,
    snapshot: StatusSnapshot,
}

impl App {
    fn new(root: &Path) -> Self {
        Self {
            selected: 0,
            mode: Mode::Browse,
            name: String::new(),
            email: String::new(),
            message: String::new(),
            snapshot: StatusSnapshot::collect(root),
        }
    }

    fn selected_step(&self) -> StepKind {
        StepKind::ALL[self.selected]
    }

    fn refresh(&mut self, root: &Path) {
        self.snapshot = StatusSnapshot::collect(root);
    }

    fn handle_key(&mut self, key: KeyEvent, root: &Path) -> Action {
        if key.kind != KeyEventKind::Press {
            return Action::None;
        }

        match self.mode {
            Mode::Browse => self.handle_browse_key(key, root),
            Mode::EditName | Mode::EditEmail => self.handle_edit_key(key),
        }
    }

    fn handle_browse_key(&mut self, key: KeyEvent, root: &Path) -> Action {
        match key.code {
            KeyCode::Char('q') | KeyCode::Esc => Action::Quit,
            KeyCode::Char('r') => Action::Refresh,
            KeyCode::Down | KeyCode::Char('j') => {
                self.selected = (self.selected + 1) % StepKind::ALL.len();
                Action::None
            }
            KeyCode::Up | KeyCode::Char('k') => {
                self.selected = self
                    .selected
                    .checked_sub(1)
                    .unwrap_or(StepKind::ALL.len() - 1);
                Action::None
            }
            KeyCode::Enter => {
                let step = self.selected_step();
                if step == StepKind::GitIdentity {
                    self.load_identity_form(root);
                    Action::None
                } else {
                    Action::Run(step)
                }
            }
            _ => Action::None,
        }
    }

    fn handle_edit_key(&mut self, key: KeyEvent) -> Action {
        match key.code {
            KeyCode::Esc => {
                self.mode = Mode::Browse;
                self.message = "Identity edit cancelled.".to_string();
                Action::None
            }
            KeyCode::Backspace => {
                self.active_input_mut().pop();
                Action::None
            }
            KeyCode::Char(character) => {
                if !character.is_control() {
                    self.active_input_mut().push(character);
                }
                Action::None
            }
            KeyCode::Enter if self.mode == Mode::EditName => {
                if self.name.trim().is_empty() {
                    self.message = "Name cannot be empty.".to_string();
                } else {
                    self.mode = Mode::EditEmail;
                    self.message.clear();
                }
                Action::None
            }
            KeyCode::Enter => {
                let name = self.name.trim().to_string();
                let email = self.email.trim().to_string();
                if !valid_identity_value(&name) {
                    self.mode = Mode::EditName;
                    self.message = "Name cannot be empty or contain a newline.".to_string();
                    return Action::None;
                }
                if !valid_identity_value(&email) || !email.contains('@') {
                    self.message = "Enter a valid email address.".to_string();
                    return Action::None;
                }
                self.mode = Mode::Browse;
                Action::SaveIdentity { name, email }
            }
            _ => Action::None,
        }
    }

    fn active_input_mut(&mut self) -> &mut String {
        if self.mode == Mode::EditName {
            &mut self.name
        } else {
            &mut self.email
        }
    }

    fn load_identity_form(&mut self, root: &Path) {
        let identity = root.join("config/git/identity.local");
        self.name = git_config_value(Some(&identity), "user.name")
            .or_else(|| git_config_value(None, "user.name"))
            .unwrap_or_default();
        self.email = git_config_value(Some(&identity), "user.email")
            .or_else(|| git_config_value(None, "user.email"))
            .unwrap_or_default();
        self.mode = Mode::EditName;
        self.message.clear();
    }
}

fn main() -> Result<(), Box<dyn Error>> {
    let arguments: Vec<String> = env::args().skip(1).collect();
    if arguments == ["--version"] {
        println!("server-onboarding {APP_VERSION}");
        return Ok(());
    }
    if !arguments.is_empty() && arguments != ["--status"] {
        return Err(format!("unknown argument: {}", arguments[0]).into());
    }

    let root = repository_root()?;
    if arguments == ["--status"] {
        print_status(&StatusSnapshot::collect(&root));
        return Ok(());
    }
    if !io::stdin().is_terminal() || !io::stdout().is_terminal() {
        return Err("onboarding requires an interactive terminal".into());
    }

    install_panic_hook();
    let mut terminal = enter_terminal()?;
    let result = run(&mut terminal, &root);
    let restore_result = leave_terminal(&mut terminal);
    restore_result?;
    result?;
    Ok(())
}

fn run(terminal: &mut Tui, root: &Path) -> io::Result<()> {
    let mut app = App::new(root);

    loop {
        terminal.draw(|frame| render(frame, &app))?;
        let Event::Key(key) = event::read()? else {
            continue;
        };

        match app.handle_key(key, root) {
            Action::None => {}
            Action::Quit => return Ok(()),
            Action::Refresh => {
                app.refresh(root);
                app.message = "Status refreshed.".to_string();
            }
            Action::SaveIdentity { name, email } => {
                match save_git_identity(root, &name, &email) {
                    Ok(()) => {
                        app.message = "Identity saved locally. Run Server convergence to apply it."
                            .to_string();
                    }
                    Err(error) => app.message = format!("Could not save identity: {error}"),
                }
                app.refresh(root);
            }
            Action::Run(step) => {
                leave_terminal(terminal)?;
                let status = run_step(root, step);
                *terminal = enter_terminal()?;
                terminal.clear()?;
                app.refresh(root);
                app.message = match status {
                    Ok(true) => format!("{} finished successfully.", step.title()),
                    Ok(false) => format!("{} exited without completing.", step.title()),
                    Err(error) => format!("Could not run {}: {error}", step.title()),
                };
            }
        }
    }
}

fn render(frame: &mut Frame<'_>, app: &App) {
    let areas = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),
            Constraint::Min(10),
            Constraint::Length(8),
            Constraint::Length(3),
        ])
        .split(frame.area());

    let progress = format!(
        " Server onboarding  {}/{} complete ",
        app.snapshot.completed_count(),
        StepKind::ALL.len()
    );
    frame.render_widget(
        Paragraph::new("Interactive setup for steps that require a human")
            .block(Block::default().borders(Borders::ALL).title(progress)),
        areas[0],
    );

    let items = StepKind::ALL.iter().map(|step| {
        let (symbol, style) = if app.snapshot.complete(*step) {
            ("✓", Style::default().fg(Color::Green))
        } else {
            ("○", Style::default().fg(Color::Yellow))
        };
        ListItem::new(Line::from(vec![
            Span::styled(format!("{symbol} "), style),
            Span::raw(step.title()),
        ]))
    });
    let list = List::new(items)
        .block(Block::default().borders(Borders::ALL).title(" Steps "))
        .highlight_symbol("> ")
        .highlight_style(Style::default().add_modifier(Modifier::REVERSED));
    let mut state = ListState::default().with_selected(Some(app.selected));
    frame.render_stateful_widget(list, areas[1], &mut state);

    render_details(frame, areas[2], app);

    let help = if app.mode == Mode::Browse {
        "↑/↓ or j/k move   Enter run/edit   r refresh   q quit"
    } else {
        "Type a value   Enter continue/save   Esc cancel"
    };
    frame.render_widget(
        Paragraph::new(help)
            .style(Style::default().fg(Color::Cyan))
            .block(Block::default().borders(Borders::ALL).title(" Keys ")),
        areas[3],
    );
}

fn render_details(frame: &mut Frame<'_>, area: Rect, app: &App) {
    if app.mode != Mode::Browse {
        let active_name = app.mode == Mode::EditName;
        let lines = vec![
            Line::from(vec![
                Span::styled(
                    "Name:  ",
                    if active_name {
                        Style::default()
                            .fg(Color::Cyan)
                            .add_modifier(Modifier::BOLD)
                    } else {
                        Style::default()
                    },
                ),
                Span::raw(&app.name),
            ]),
            Line::from(vec![
                Span::styled(
                    "Email: ",
                    if active_name {
                        Style::default()
                    } else {
                        Style::default()
                            .fg(Color::Cyan)
                            .add_modifier(Modifier::BOLD)
                    },
                ),
                Span::raw(&app.email),
            ]),
            Line::raw(&app.message),
        ];
        frame.render_widget(
            Paragraph::new(lines)
                .block(
                    Block::default()
                        .borders(Borders::ALL)
                        .title(" Git identity "),
                )
                .wrap(Wrap { trim: false }),
            area,
        );
        return;
    }

    let step = app.selected_step();
    let mut lines = vec![
        Line::raw(step.description()),
        Line::raw(""),
        Line::styled(
            app.snapshot.detail(step),
            if app.snapshot.complete(step) {
                Style::default().fg(Color::Green)
            } else {
                Style::default().fg(Color::Yellow)
            },
        ),
    ];
    if let Some(command) = step.command() {
        lines.push(Line::raw(format!("Command: {command}")));
    }
    if !app.message.is_empty() {
        lines.push(Line::raw(format!("Last result: {}", app.message)));
    }
    frame.render_widget(
        Paragraph::new(lines)
            .block(Block::default().borders(Borders::ALL).title(" Details "))
            .wrap(Wrap { trim: false }),
        area,
    );
}

fn print_status(snapshot: &StatusSnapshot) {
    for step in StepKind::ALL {
        let marker = if snapshot.complete(step) { "ok" } else { "  " };
        println!("[{marker}] {}", step.title());
    }
}

fn command_succeeds(program: &str, arguments: &[&str]) -> bool {
    Command::new(program)
        .args(arguments)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .is_ok_and(|status| status.success())
}

fn pi_auth_is_present() -> bool {
    let Some(home) = home_directory() else {
        return false;
    };
    let auth = home.join(".pi/agent/auth.json");
    fs::metadata(auth).is_ok_and(|metadata| {
        metadata.is_file() && metadata.len() > 0 && metadata.permissions().mode() & 0o777 == 0o600
    })
}

fn convergence_is_current(root: &Path, identity_saved: bool) -> bool {
    let Some(home) = home_directory() else {
        return false;
    };
    let state_home = env::var_os("XDG_STATE_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|| home.join(".local/state"));
    let log = state_home.join("server-config/logs/verify.log");
    let Ok(content) = fs::read_to_string(&log) else {
        return false;
    };
    if !parse_convergence_recap(&content) {
        return false;
    }
    if !identity_saved {
        return true;
    }

    let identity = root.join("config/git/identity.local");
    let Ok(log_time) = fs::metadata(log).and_then(|metadata| metadata.modified()) else {
        return false;
    };
    let Ok(identity_time) = fs::metadata(identity).and_then(|metadata| metadata.modified()) else {
        return false;
    };
    log_time >= identity_time
}

fn parse_convergence_recap(content: &str) -> bool {
    content.lines().any(|line| {
        line.contains("changed=0") && line.contains("unreachable=0") && line.contains("failed=0")
    })
}

fn valid_git_identity_file(path: &Path) -> bool {
    if !fs::metadata(path)
        .is_ok_and(|metadata| metadata.is_file() && metadata.permissions().mode() & 0o777 == 0o600)
    {
        return false;
    }
    git_config_value(Some(path), "user.name").is_some()
        && git_config_value(Some(path), "user.email").is_some()
}

fn git_config_value(file: Option<&Path>, key: &str) -> Option<String> {
    let mut command = Command::new("git");
    command.arg("config");
    if let Some(file) = file {
        command.arg("--file").arg(file);
    } else {
        command.args(["--global", "--includes"]);
    }
    let output = command.arg("--get").arg(key).output().ok()?;
    if !output.status.success() {
        return None;
    }
    let value = String::from_utf8(output.stdout).ok()?.trim().to_string();
    (!value.is_empty()).then_some(value)
}

fn valid_identity_value(value: &str) -> bool {
    !value.trim().is_empty() && !value.contains(['\n', '\r'])
}

fn save_git_identity(root: &Path, name: &str, email: &str) -> Result<(), Box<dyn Error>> {
    if !valid_identity_value(name) || !valid_identity_value(email) || !email.contains('@') {
        return Err("invalid Git identity".into());
    }

    let relative = Path::new("config/git/identity.local");
    let ignored = Command::new("git")
        .arg("-C")
        .arg(root)
        .args(["check-ignore", "--quiet"])
        .arg(relative)
        .status()?;
    if !ignored.success() {
        return Err("config/git/identity.local is not ignored by Git".into());
    }

    let path = root.join(relative);
    let parent = path.parent().ok_or("identity path has no parent")?;
    fs::create_dir_all(parent)?;
    OpenOptions::new()
        .create(true)
        .truncate(true)
        .write(true)
        .mode(0o600)
        .open(&path)?;
    fs::set_permissions(&path, fs::Permissions::from_mode(0o600))?;

    for (key, value) in [("user.name", name), ("user.email", email)] {
        let status = Command::new("git")
            .args(["config", "--file"])
            .arg(&path)
            .arg(key)
            .arg(value)
            .status()?;
        if !status.success() {
            return Err(format!("git config failed while writing {key}").into());
        }
    }
    Ok(())
}

fn run_step(root: &Path, step: StepKind) -> io::Result<bool> {
    let Some(command) = step.command() else {
        return Ok(false);
    };

    println!("\n{}\n", step.description());
    if step == StepKind::Pi {
        println!("Inside Pi, run /login. Exit Pi when authentication is complete.\n");
    } else if step == StepKind::Codex {
        println!(
            "Complete device sign-in in a browser. Pair Remote Control after login with `codex remote-control start` and `codex remote-control pair`.\n"
        );
    }
    println!("Running: {command}\n");

    external_command(root, command)
        .status()
        .map(|status| status.success())
}

fn external_command(root: &Path, command: &str) -> Command {
    let mut process = Command::new("/bin/zsh");
    process
        .args(["-lc", command])
        .current_dir(root)
        .stdin(Stdio::inherit())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit());
    process
}

fn repository_root() -> Result<PathBuf, Box<dyn Error>> {
    let root = env::var_os("SERVER_CONFIG_ROOT")
        .map(PathBuf::from)
        .unwrap_or(env::current_dir()?);
    if !root.join("playbook.yml").is_file() || !root.join(".gitignore").is_file() {
        return Err(format!("{} is not a server-config checkout", root.display()).into());
    }
    Ok(root)
}

fn home_directory() -> Option<PathBuf> {
    env::var_os("HOME").map(PathBuf::from)
}

fn enter_terminal() -> io::Result<Tui> {
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen)?;
    let mut terminal = Terminal::new(CrosstermBackend::new(stdout))?;
    terminal.clear()?;
    Ok(terminal)
}

fn leave_terminal(terminal: &mut Tui) -> io::Result<()> {
    disable_raw_mode()?;
    execute!(terminal.backend_mut(), LeaveAlternateScreen)?;
    terminal.show_cursor()
}

fn install_panic_hook() {
    let original = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |panic_info| {
        let _ = disable_raw_mode();
        let _ = execute!(io::stdout(), LeaveAlternateScreen);
        original(panic_info);
    }));
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::backend::TestBackend;
    use tempfile::tempdir;

    #[test]
    fn convergence_requires_a_clean_second_recap() {
        assert!(parse_convergence_recap(
            "localhost : ok=78 changed=0 unreachable=0 failed=0 skipped=17"
        ));
        assert!(!parse_convergence_recap(
            "localhost : ok=78 changed=1 unreachable=0 failed=0 skipped=17"
        ));
        assert!(!parse_convergence_recap(
            "localhost : ok=78 changed=0 unreachable=0 failed=1 skipped=17"
        ));
    }

    #[test]
    fn navigation_wraps_in_both_directions() {
        let root = Path::new(".");
        let mut app = App {
            selected: 0,
            mode: Mode::Browse,
            name: String::new(),
            email: String::new(),
            message: String::new(),
            snapshot: StatusSnapshot::default(),
        };
        app.handle_key(KeyEvent::from(KeyCode::Up), root);
        assert_eq!(app.selected, StepKind::ALL.len() - 1);
        app.handle_key(KeyEvent::from(KeyCode::Down), root);
        assert_eq!(app.selected, 0);
    }

    #[test]
    fn renders_status_without_personal_values() {
        let backend = TestBackend::new(100, 30);
        let mut terminal = Terminal::new(backend).expect("test terminal");
        let app = App {
            selected: 0,
            mode: Mode::Browse,
            name: String::new(),
            email: String::new(),
            message: String::new(),
            snapshot: StatusSnapshot {
                tailscale: true,
                github: true,
                ..StatusSnapshot::default()
            },
        };
        terminal.draw(|frame| render(frame, &app)).expect("render");
        let screen = terminal
            .backend()
            .buffer()
            .content()
            .iter()
            .map(|cell| cell.symbol())
            .collect::<String>();
        assert!(screen.contains("Server onboarding"));
        assert!(screen.contains("GitHub CLI"));
        assert!(screen.contains("Codex CLI"));
        assert!(screen.contains("2/7 complete"));
    }

    #[test]
    fn external_steps_use_a_non_interactive_login_shell() {
        let command = external_command(Path::new("/tmp"), "true");
        assert_eq!(command.get_program(), "/bin/zsh");
        assert_eq!(
            command
                .get_args()
                .map(|argument| argument.to_string_lossy())
                .collect::<Vec<_>>(),
            ["-lc", "true"]
        );
    }

    #[test]
    fn saves_only_name_and_email_to_an_ignored_file() {
        let directory = tempdir().expect("temporary directory");
        let root = directory.path();
        fs::create_dir_all(root.join("config/git")).expect("config directory");
        fs::write(root.join(".gitignore"), "config/git/identity.local\n").expect("gitignore");
        fs::write(root.join("playbook.yml"), "---\n").expect("playbook");
        assert!(
            Command::new("git")
                .arg("init")
                .arg("--quiet")
                .arg(root)
                .status()
                .expect("git init")
                .success()
        );

        save_git_identity(root, "Test User", "test@example.invalid").expect("save identity");
        let identity = root.join("config/git/identity.local");
        assert_eq!(
            fs::metadata(&identity)
                .expect("metadata")
                .permissions()
                .mode()
                & 0o777,
            0o600
        );
        let keys = Command::new("git")
            .args(["config", "--file"])
            .arg(&identity)
            .args(["--name-only", "--list"])
            .output()
            .expect("read identity keys");
        assert!(keys.status.success());
        assert_eq!(
            String::from_utf8(keys.stdout).expect("utf8"),
            "user.name\nuser.email\n"
        );
    }
}
