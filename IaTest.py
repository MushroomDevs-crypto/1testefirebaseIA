import tweepy
import os
from time import sleep
import openai
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db

# Carrega variáveis de ambiente e
load_dotenv()

# Credenciais da API do X (Twitter)
consumer_key = os.getenv("TWITTER_API_KEY")
consumer_secret = os.getenv("TWITTER_API_SECRET")
access_token = os.getenv("TWITTER_ACCESS_TOKEN")
access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
bearer_token = os.getenv("TWITTER_BEARER_TOKEN")

# Credenciais da API do ChatGPT (OpenAI)
openai.api_key = os.getenv("OPENAI_API_KEY")

# Inicializa o Firebase usando variáveis de ambiente
def initialize_firebase():
    # Cria um dicionário com as credenciais do Firebase a partir das variáveis de ambiente
    cred_dict = {
        "type": os.getenv("FIREBASE_TYPE"),
        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
        "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
        "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),  # Corrige quebras de linha
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "client_id": os.getenv("FIREBASE_CLIENT_ID"),
        "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
        "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
    }
    # Inicializa o Firebase com as credenciais
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://iatestefirebase-default-rtdb.firebaseio.com/'  # Substitua pela URL do seu banco de dados
    })

# Função para obter o último ID processado
def get_last_processed_id():
    ref = db.reference('last_processed_id')
    return ref.get()

# Função para salvar o último ID processado
def save_last_processed_id(last_id):
    ref = db.reference('last_processed_id')
    ref.set(last_id)

# Inicializa o cliente do Twitter
client = tweepy.Client(
    bearer_token=bearer_token,
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    access_token=access_token,
    access_token_secret=access_token_secret,
    wait_on_rate_limit=True,
)

# Função para obter o ID do usuário autenticado
def get_user_id():
    try:
        user = client.get_user(username="Mushroomdevs")  # Substitua pelo nome de usuário do bot
        return user.data.id
    except Exception as e:
        print(f"Erro ao obter ID do usuário: {e}")
        return None

# Gera uma resposta usando o ChatGPT
def generate_chatgpt_response(tweet_text):
    try:
        system_prompt = """
        Você é um bot inteligente que responde com sabedoria e clareza. Use um tom profissional, mas amigável.
        
        Formato de resposta:
        - Comece com uma introdução breve.
        - Dê uma resposta objetiva e clara.
        - Conclua com uma frase de fechamento amigável.

        Certifique-se de que sua resposta seja relevante ao texto fornecido e que tenha no máximo 280 caracteres.
        """
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": tweet_text},
            ],
        )
        full_response = response.choices[0].message.content.strip()
        if len(full_response) > 280:
            return full_response[:277] + "..."
        return full_response
    except Exception as e:
        print(f"Erro ao gerar resposta com ChatGPT: {e}")
        return "Desculpe, algo deu errado ao gerar minha resposta."

# Função para responder a menções
def reply_to_mentions():
    user_id = get_user_id()
    if not user_id:
        print("Não foi possível obter o ID do usuário.")
        return

    last_mention_id = get_last_processed_id()
    print(f"Último ID processado: {last_mention_id}")

    try:
        mentions = client.get_users_mentions(
            id=user_id,
            since_id=last_mention_id,
            max_results=20,
            tweet_fields=["id", "author_id", "referenced_tweets"],
        )
        
        if mentions.data:
            print(f"Encontradas {len(mentions.data)} menções.")
            for mention in mentions.data:
                referenced_tweet_id = None

                if mention.referenced_tweets:
                    for ref in mention.referenced_tweets:
                        if ref["type"] == "replied_to":
                            referenced_tweet_id = ref["id"]
                            break
                
                if not referenced_tweet_id:
                    print(f"Não foi possível encontrar o tweet original para a menção {mention.id}.")
                    continue
                
                original_tweet = client.get_tweet(id=referenced_tweet_id, tweet_fields=["text"]).data
                if not original_tweet:
                    print(f"Não foi possível obter o tweet original {referenced_tweet_id}.")
                    continue
                
                print(f"Gerando resposta para o tweet {original_tweet.id}...")
                response_text = generate_chatgpt_response(original_tweet.text)

                try:
                    print(f"Respondendo ao tweet {mention.id}...")
                    client.create_tweet(
                        text=response_text,
                        in_reply_to_tweet_id=mention.id,
                    )
                    print(f"Resposta enviada para o tweet {mention.id}.")
                except Exception as e:
                    print(f"Erro ao responder ao tweet {mention.id}: {e}")
                
                save_last_processed_id(mention.id)
        else:
            print("Nenhuma menção nova encontrada.")
    except tweepy.errors.TweepyException as e:
        print(f"Erro ao buscar ou responder menções: {e}")

# Loop principal
if __name__ == "__main__":
    initialize_firebase()  # Inicializa o Firebase
    while True:
        print("Verificando menções...")
        reply_to_mentions()
        print("Aguardando 2 minutos antes da próxima verificação...")
        sleep(120)
